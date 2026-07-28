#!/usr/bin/env python3
"""
Filter and classify files in raw/inbox/ based on wiki interests.

Usage:
    python tools/filter.py              # main mode
    python tools/filter.py --dry-run    # show what would be done

Flow:
    1. Scan raw/inbox/ for files
    2. Read wiki/interests.md
    3. Use LLM to generate brief summary (3-5 sentences) + detailed report (500-800 words)
    4. Match against interests (interested / possibly interested / not interested)
    5. Generate raw/digest/brief.md with entries sorted by match level
    6. Move files to raw/digest/sources/YYYY-MM-DD/
    7. Archive old brief.md entries
    8. Clear inbox/

Output:
    - raw/digest/brief.md             — current brief with sorted entries
    - raw/digest/YYYY-MM-DD/          — file directories
    - raw/digest/brief/YYYY-MM-DD.md  — archive of old brief
"""

import re
import sys
import json
import shutil
import argparse
import os
from pathlib import Path
from datetime import date
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from _utils import (read_file, write_file, call_llm, prepare_tasks, read_results,
                     clean_task_dirs, TASK_DIR, RESULT_DIR, inject_source_url)

REPO_ROOT = Path(__file__).parent.parent
INBOX_DIR = REPO_ROOT / "raw" / "inbox"
DIGEST_DIR = REPO_ROOT / "raw" / "digest"
BRIEF_DIR = DIGEST_DIR / "brief"
BRIEF_FILE = DIGEST_DIR / "brief.md"
CATEGORIES = [
    "articles", "datasets", "docs", "books",
    "papers", "projects", "talks",
]
INTERESTS_FILE = REPO_ROOT / "wiki" / "interests.md"
LOG_FILE = REPO_ROOT / "wiki" / "log.md"
FILTER_CACHE = DIGEST_DIR / ".filter-cache.json"


def _apply_suggestions(suggested_interests, suggested_disinterests, log_fn=print):
    """Apply filter suggestions to interests.md.
    Appends new items under the appropriate section.
    """
    if not suggested_interests and not suggested_disinterests:
        return
    content = read_file(INTERESTS_FILE)
    if not content:
        content = "# 兴趣点\n\n## 兴趣列表\n\n## 排除列表\n"
    
    lines = content.split('\n')
    new_lines = list(lines)
    insertions = 0
    
    for si in suggested_interests:
        name = si if isinstance(si, str) else si.get("name", "")
        if not name:
            continue
        kw_str = name if isinstance(si, str) else ", ".join(si.get("keywords", []))
        if any(name in l for l in lines):
            log_fn(f"  ⏭️  兴趣已存在: {name}")
            continue
        inserted = False
        for i, line in enumerate(new_lines):
            if line.strip() == "## 兴趣列表":
                insert_at = i + 1
                while insert_at < len(new_lines) and new_lines[insert_at].strip() == "":
                    insert_at += 1
                new_lines.insert(insert_at, f"- {name} [{kw_str}]")
                insertions += 1
                inserted = True
                log_fn(f"  + 兴趣点: {name} [{kw_str}]")
                break
        if not inserted:
            new_lines.append(f"- {name} [{kw_str}]")
            insertions += 1
    
    for sd in suggested_disinterests:
        name = sd if isinstance(sd, str) else sd.get("name", "")
        if not name:
            continue
        kw_str = name if isinstance(sd, str) else ", ".join(sd.get("keywords", []))
        if any(name in l for l in lines):
            log_fn(f"  ⏭️  排除项已存在: {name}")
            continue
        inserted = False
        for i, line in enumerate(new_lines):
            if line.strip() == "## 排除列表":
                insert_at = i + 1
                while insert_at < len(new_lines) and new_lines[insert_at].strip() == "":
                    insert_at += 1
                new_lines.insert(insert_at, f"- {name} [{kw_str}]")
                insertions += 1
                inserted = True
                log_fn(f"  + 排除项: {name} [{kw_str}]")
                break
        if not inserted:
            new_lines.append(f"- {name} [{kw_str}]")
            insertions += 1
    
    if insertions > 0:
        write_file(INTERESTS_FILE, '\n'.join(new_lines))
        log_fn(f"✅ 已合入 {insertions} 个新条目到 interests.md")
    else:
        log_fn("  无新条目需要合入。")


def parse_interests(content: str) -> list[dict]:
    """Parse interests/disinterests from wiki/interests.md content.

    Format:
        ## 兴趣列表
        - 名称 [kw1, kw2, ...]

        ## 排除列表
        ### 方向/细分领域
        - 名称 [kw1, kw2, ...]
    """
    entries = []
    current_category = None
    current_subcategory = None
    VALID_SECTIONS = {"兴趣列表", "排除列表"}

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        cat_match = re.match(r'^## (.+)$', line)
        if cat_match:
            current_category = cat_match.group(1).strip() if cat_match.group(1).strip() in VALID_SECTIONS else None
            current_subcategory = None
            continue

        sub_match = re.match(r'^### (.+)$', line)
        if sub_match and current_category:
            current_subcategory = sub_match.group(1).strip()
            continue

        if current_category is None:
            continue

        item_match = re.match(r'^-\s+(.+?)(?:\s*\[([^\]]*)\])?\s*$', line)
        if item_match:
            name = item_match.group(1).strip()
            kw_str = item_match.group(2)
            is_exclusion = current_category == "排除列表"
            entries.append({
                "name": name,
                "weight": 0.9 if is_exclusion else 0.5,
                "keywords": [k.strip() for k in kw_str.split(",")] if kw_str else [],
                "description": "",
                "category": current_category or "未分类",
                "subcategory": current_subcategory or "",
            })

    return entries


def get_file_preview(file_path: Path, max_chars: int = 2500) -> str:
    """Get compact file preview for LLM. Papers: abstract + title. Others: first max_chars chars."""
    content = read_file(file_path)
    if len(content) <= max_chars:
        return content

    # Detect paper: has Abstract section
    has_abstract = re.search(r'##\s+[Aa]bstract', content[:5000], re.MULTILINE)

    if not has_abstract:
        # Non-paper: return head + tail (intro + conclusion signals)
        head = content[:max_chars]
        tail = content[-1000:] if len(content) > max_chars + 2000 else ""
        result = head
        if tail:
            result += f"\n\n[...skipped {len(content) - max_chars - 1000} chars...]\n\n{tail}"
        return result[:max_chars + 1500]

    # Paper: extract YAML frontmatter + Abstract + first N chars of main body
    parts = []
    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if yaml_match:
        parts.append(yaml_match.group(0))

    # Extract Abstract section (full)
    abs_match = re.search(
        r'(##\s+[Aa]bstract|##\s+摘要|\*\*摘要\*\*)'
        r'(.*?)(?=\n##\s+\d?\s*[A-Z]|\n##\s+[A-Z]|\Z)',
        content, re.DOTALL
    )
    if abs_match:
        parts.append(abs_match.group(0))

    result = '\n\n'.join(parts)
    return result[:max_chars + 2000] if result else content[:max_chars]


def extract_source_url(file_path: Path) -> str:
    """Try to extract URL from file metadata, filename, or content.
    Priority: YAML frontmatter > content URL > filename heuristic."""
    content = read_file(file_path)
    lines = content.split('\n')

    # 1. YAML frontmatter: url: "..."
    if content.startswith('---'):
        end = content.find('---', 3)
        if end != -1:
            for line in content[3:end].split('\n'):
                m = re.match(r'url:\s*["\']?(https?://\S+)["\']?\s*', line.strip())
                if m:
                    return m.group(1).rstrip('"\'"')

    # 2. Content lines: url: / source_url: / bare http links
    for line in lines[:100]:
        line = line.strip()
        m = re.match(r'(?:url|URL|source_url):\s*["\']?(https?://\S+)["\']?\s*', line)
        if m:
            return m.group(1).rstrip('"\'"')
        if line.startswith('http') and '://' in line:
            return line.split()[0]

    # 3. Filename heuristic (last resort)
    name = file_path.stem
    for word in name.split('-'):
        if word.startswith('http') or word.startswith('www.'):
            return f"https://{word}"
        if '.' in word and any(tld in word for tld in ['.com', '.org', '.net', '.io']):
            return f"https://{word}"

    return file_path.as_posix()


def build_analyze_prompt(file_path: Path, interests_desc: str, disinterests_desc: str = "") -> str:
    """Build the LLM prompt for analyzing a file."""
    preview = get_file_preview(file_path)
    source_url = extract_source_url(file_path)

    is_multientry = any(kw in preview.lower() for kw in [
        "arxiv", "paper", "list", "summary", "newsletter", "digest",
        "bulletin", "weekly", "daily", "top", "most", "recent",
    ])
    entry_count_hint = "\nExtract EACH distinct item as a separate entry." if is_multientry else "\nReturn exactly ONE entry in the array."

    return f"""分析研究材料，返回JSON数组。

每个JSON对象字段说明：
- title: 原文标题（英文）
- title_cn: 中文翻译标题
- source_url: 原文来源URL
- figure_url: 框架图/架构图URL（从文档预览中找第一个图表图片URL，没有则空字符串）
- figure_caption: 框架图/架构图的中文说明（直接在文档中寻找该图片对应的标题文字并翻译为中文，不要用"Refer to caption"）
- domain: 所属领域
- keywords: 关键词列表
- match_level: 匹配程度（interested / possibly_interested / not_interested）
- matched_interests: 匹配到的兴趣条目名称列表
- reason: 匹配理由（必须具体，写明"文档的XXX部分讨论了XXX"）
- brief: 3-5句中文摘要（简述核心贡献和方法）
- detailed_report: 300-500字中文详细分析，**必须用直白语言描述论文主要思路和方法流程**。包含：要解决的问题（1句）、**核心思路**（用"简单来说就是..."的方式解释设计动机，2-3句）、**方法流程**（按步骤说明输入→处理→输出，3-5句）、效果/实验结果（1-2句）、局限性/潜在问题（1句）。避免堆砌术语，要让不熟悉该方向的读者也能理解
- suggested_category: 分类（papers/articles/talks/books/docs/projects/datasets）
- suggested_new_interests: 建议新增的兴趣点（可选）
- suggested_new_disinterests: 建议新增的排除项（可选）

{entry_count_hint}

兴趣列表（据此判断匹配）:
{interests_desc or "无"}

排除列表（命中则强制 not_interested）:
{disinterests_desc or "无"}

文档({file_path.name}):
{preview}

返回JSON数组，不要代码块。

匹配规则（必须严格遵守）:
- 只标记 interested 当文档核心主题与兴趣条目直接对应。关键词只是辅助，不能仅凭关键词出现就判定感兴趣
- possibly_interested 要求文档至少30%内容与兴趣条目相关，而非仅提及
- 宁可漏判不可误判：拿不准时标记 not_interested
- 不要发散猜测：不要因为标题/摘要提到了兴趣领域的上位概念就标记感兴趣（如兴趣是"3D高斯泼溅"，不要因为文档提到"3D视觉"就标记）
- 匹配理由必须具体：写明"文档的XXX部分直接讨论了XXX兴趣条目"，而非"文档涉及相关领域"
- 如果「兴趣」为空，matched_interests 返回空数组 []
- 如果文档涉及的兴趣/排除项不在上方列表中，可建议新增到 suggested_new_interests / suggested_new_disinterests（可选）
- brief 和 detailed_report **必须填写完整**，不能为空"""


def parse_analyze_response(raw: str, file_path: Path, source_url: str = "") -> list[dict]:
    """Parse LLM response into structured results."""
    clean = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    clean = re.sub(r"\s*```$", "", clean.strip())
    data = json.loads(clean)
    if not isinstance(data, list):
        data = [data]

    results = []
    for entry in data:
        brief = entry.get("brief", "").strip()
        detailed = entry.get("detailed_report", "").strip()
        if not brief:
            print(f"  ⚠️  {file_path.name}: brief 为空")
        if not detailed:
            print(f"  ⚠️  {file_path.name}: detailed_report 为空")
        results.append({
            "file": file_path,
            "item_id": entry.get("item_id", 1),
            "match_level": entry.get("match_level", "not_interested"),
            "matched_interests": entry.get("matched_interests", []),
            "reason": entry.get("reason", ""),
            "suggested_category": entry.get("suggested_category", "papers"),
            "title": entry.get("title", file_path.stem),
            "title_cn": entry.get("title_cn", ""),
            "brief": entry.get("brief", ""),
            "detailed_report": entry.get("detailed_report", ""),
            "source_url": entry.get("source_url") or source_url,
            "figure_url": entry.get("figure_url", ""),
            "figure_caption": entry.get("figure_caption", ""),
            "domain": entry.get("domain", ""),
            "keywords": entry.get("keywords", []),
            "suggested_new_interests": entry.get("suggested_new_interests", []),
            "suggested_new_disinterests": entry.get("suggested_new_disinterests", []),
        })
    return results


def analyze_file(file_path: Path, interests_desc: str, disinterests_desc: str = "") -> list[dict]:
    """Use LLM to analyze file. Direct mode (calls LLM API)."""
    if not interests_desc.strip():
        print("  Warning: No interests defined. Generating summary only.")

    prompt = build_analyze_prompt(file_path, interests_desc, disinterests_desc)
    source_url = extract_source_url(file_path)

    try:
        raw = call_llm(prompt, max_tokens=4096)
        return parse_analyze_response(raw, file_path, source_url)
    except Exception as e:
        print(f"  ⚠️  LLM failed for {file_path.name}: {e}")
        raise RuntimeError(f"LLM analysis failed for {file_path.name}")


def _normalize_arxiv_url(url: str) -> str:
    """Fix malformed arxiv HTML URLs and handle /assets/ subpath fallback.

    arXiv HTML (arxiv.org/html) serves images at root level or under /figures/,
    NEVER under /assets/. Paths with /assets/ come from papers without an
    arXiv HTML version (arxiv2md PDF extraction) — redirect to ar5iv mirror
    which preserves the /assets/ structure.

    Also fixes the arxiv2md double /html/ prefix bug:
      https://arxiv.org/html//html/2311.10091/assets/x2.png
        → https://ar5iv.labs.arxiv.org/html/2311.10091/assets/x2.png
    """
    url = re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', url)
    if '/assets/' in url and 'arxiv.org/html/' in url:
        url = url.replace('https://arxiv.org/html/', 'https://ar5iv.labs.arxiv.org/html/')
    return url


def _extract_figure_from_source(item: dict, source_url: str = "") -> tuple[str, str, str]:
    """Extract (url, short_caption, full_caption) from source file or result fields.
    
    Stores extracted data back to item dict for persistence across rebuilds.
    Local figure paths are automatically converted to arXiv HTML URLs.
    """
    url = item.get("figure_url", "")
    caption = item.get("figure_caption", "")
    cached = item.get("_figure_cached", False)

    # If already cached (from previous extraction), reuse
    if cached and url:
        short = item.get("_figure_short", _shorten(caption) if caption else "")
        return url, short, caption

    def _shorten(text: str, maxlen: int = 80) -> str:
        first = re.split(r'[.。!！?？]', text)[0].strip()
        if len(first) <= maxlen:
            return first
        mid = text.find('. ', maxlen // 2)
        if maxlen // 2 < mid < maxlen + 5:
            return text[:mid+1]
        return first[:maxlen-3] + "..."

    def _fix_local_path(img_url: str) -> str:
        """Convert local figures/xxx.png to arXiv HTML URL.
        
        arXiv HTML serves images at root level or under /figures/.
        Paths under /assets/ come from papers without an arXiv HTML version
        (arxiv2md PDF extraction) — fall back to ar5iv mirror which preserves
        the /assets/ structure.
        """
        if not img_url.startswith("figures/") and not img_url.startswith("assets/"):
            return img_url
        # Extract arxiv ID from item's source_url or file path
        src = source_url or item.get("source_url", "") or str(item.get("file", ""))
        aid = re.search(r'(\d{4}\.\d{4,5})', src)
        if aid:
            aid = aid.group(1)
            fname = img_url.rsplit("/", 1)[-1]
            prefix = img_url.replace(fname, '')
            base = "https://ar5iv.labs.arxiv.org/html" if prefix.startswith("assets/") else "https://arxiv.org/html"
            return _normalize_arxiv_url(f"{base}/{aid}/{prefix}{fname}")
        return _normalize_arxiv_url(img_url)

    def _find_caption(fp: Path) -> tuple[str, str, str]:
        if not fp or not fp.exists():
            return "", "", ""
        content = read_file(fp)
        lines = content.split("\n")
        img_re = re.compile(r'!\[([^\]]*)\]\(((?:https?://[^)]+|figures/[^)]+|assets/[^)]+|[^)]+\.(?:png|jpg|jpeg|svg)))\)')

        def extract_at(i: int) -> tuple[str, str, str] | None:
            """Extract image info at line i using same logic as original."""
            m = img_re.search(lines[i])
            if not m:
                return None
            img_url, alt = m.group(2), m.group(1)
            img_url = _normalize_arxiv_url(img_url)
            if any(kw in img_url.lower() for kw in ["equation", "eqn", "formula", "icon"]):
                return None
            img_url = _fix_local_path(img_url)
            for la in range(1, 4):
                if i + la >= len(lines):
                    continue
                nxt = lines[i + la].strip()
                if nxt and not nxt.startswith("![") and not nxt.startswith("#"):
                    nxt = re.sub(r'^(?:Figure|Fig\.?|表|图)\s*\d+[\.:]\s*', '', nxt, flags=re.IGNORECASE).strip()
                    if len(nxt) > 10 and not re.match(r'^[a-z]{1,4}\s', nxt):
                        short = _shorten(nxt)
                        _cache_figure(item, img_url, nxt, short)
                        return (img_url, short, nxt)
            if alt not in ("Refer to caption", "Uncaptioned image", ""):
                short = _shorten(alt)
                _cache_figure(item, img_url, alt, short)
                return (img_url, short, alt)
            fname = img_url.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("-", " ").replace("_", " ")
            guess = _guess_figure_caption(fname)
            if guess:
                _cache_figure(item, img_url, guess, guess)
                return (img_url, guess, guess)
            return None

        def caption_has_keyword(line_i: int) -> bool:
            """Check if a few lines after line_i contain pipeline/overview keywords."""
            for la in range(1, 5):
                if line_i + la >= len(lines):
                    break
                nxt = lines[line_i + la].strip()
                if any(kw in nxt.lower() for kw in
                       ["pipeline", "overview", "framework", "architecture", "method overview",
                        "our approach", "proposed approach", "system overview"]):
                    return True
            return False

        def is_non_figure(caption: str) -> bool:
            """Detect captions that describe results/comparison/ablation rather than method."""
            low = caption.lower()
            # Skip pure comparison/results figures
            if any(kw in low for kw in
                   ["comparison", "ablation", "qualitative result", "quantitative result",
                    "results on", "gallery of results", "additional result"]):
                return True
            # Skip sub-figure labels like "(a) xxx", "(b) xxx" (likely part of a results gallery)
            if re.match(r'^\([a-z]\)\s', caption):
                return True
            # Skip very short captions (< 20 chars) that likely aren't method descriptions
            if len(caption) < 20:
                return True
            return False

        # Priority 1: Method section figure whose caption contains pipeline/overview keywords
        method_idx = -1
        for i, line in enumerate(lines):
            if re.match(r'^##\s+\d+\.?\s*Method|^##\s+Method\b', line, re.IGNORECASE):
                method_idx = i
                break
        if method_idx >= 0:
            for i in range(method_idx, min(len(lines), method_idx + 80)):
                if lines[i].startswith("## ") and i > method_idx + 1:
                    break
                if img_re.search(lines[i]) and caption_has_keyword(i):
                    result = extract_at(i)
                    if result and result[0]:
                        return result

        # Priority 2: any figure with pipeline/overview keywords
        for i, line in enumerate(lines):
            m = img_re.search(line)
            if m and caption_has_keyword(i):
                result = extract_at(i)
                if result and result[0]:
                    return result

        # Priority 3: first figure in Method section (but skip results/comparison figures)
        if method_idx >= 0:
            for i in range(method_idx, min(len(lines), method_idx + 80)):
                if lines[i].startswith("## ") and i > method_idx + 1:
                    break
                m = img_re.search(lines[i])
                if not m:
                    continue
                # Check caption
                for la in range(1, 4):
                    if i + la >= len(lines):
                        continue
                    cap = lines[i + la].strip()
                    if cap and not is_non_figure(cap):
                        result = extract_at(i)
                        if result and result[0]:
                            return result
                # No caption or short caption: still try
                result = extract_at(i)
                if result and result[0]:
                    return result

        # Priority 4: first valid image (original logic)
        for i in range(len(lines)):
            result = extract_at(i)
            if result and result[0]:
                return result
        return "", "", ""

    def _cache_figure(it: dict, u: str, full: str, short: str):
        it["_figure_cached"] = True
        it["figure_url"] = u
        it["figure_caption"] = full
        it["_figure_short"] = short

    def _is_figure_suitable(fig_url: str, fig_caption: str) -> bool:
        """Reject figures that are results/comparison/ablation/limitation rather than method."""
        if not fig_url:
            return False
        url_low = fig_url.lower()
        # URL path indicators of non-method figures
        if any(kw in url_low for kw in
               ["comparison", "ablation", "sota", "limit", "limitation",
                "result", "gallery", "qualitative"]):
            return False
        # Caption-based rejection
        if fig_caption:
            low = fig_caption.lower()
            if any(kw in low for kw in
                   ["comparison", "ablation", "qualitative result",
                    "quantitative result", "results on", "gallery of results",
                    "additional result", "limitation", "failure case"]):
                return False
            if re.match(r'^\([a-z]\)\s', fig_caption):
                return False
        return True

    # If item has Chinese figure_caption from subagent, validate it first
    if url and caption and len(caption) > 5:
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', caption))
        if has_chinese:
            if _is_figure_suitable(url, caption):
                short = item.get("_figure_short", _shorten(caption))
                item["_figure_cached"] = True
                return url, short, caption
            # Subagent's figure is not suitable — clear so _find_caption gets a chance
            url = ""
            caption = ""

    # Try original file path
    if isinstance(item.get("file"), Path):
        r = _find_caption(item["file"])
        if r[0]: return r

    # Try digest/sources/ paths
    fp = item.get("file")
    if isinstance(fp, Path):
        sources = Path(__file__).parent.parent / "raw/digest/sources"
        if sources.exists():
            for sd in sorted(sources.iterdir(), reverse=True):
                if sd.is_dir():
                    r = _find_caption(sd / fp.name)
                    if r[0]: return r

    # Fallback to result fields
    if url:
        if caption not in ("Refer to caption", "Uncaptioned image", ""):
            return url, _shorten(caption), caption
        guess = _guess_figure_caption(url)
        return url, guess or "框架图/流程图", guess or "框架图/流程图"
    return "", "", ""


def _guess_figure_caption(filename: str) -> str:
    """Derive a human-readable figure caption from filename patterns."""
    mapping = {
        "framework": "整体框架图",
        "pipeline": "管线流程图",
        "overview": "方法概览图",
        "architecture": "网络架构图",
        "teaser": "效果展示图",
        "results": "实验结果对比",
        "qualitative": "定性结果对比",
        "quantitative": "定量结果对比",
        "ablation": "消融实验对比",
        "comparison": "方法对比图",
        "network": "网络结构图",
        "flowchart": "算法流程图",
        "diagram": "示意图",
        "model": "模型结构图",
        "method": "方法示意图",
        "training": "训练流程",
        "inference": "推理流程",
        "vis": "可视化结果",
        "visualization": "可视化结果",
    }
    fname = filename.lower().rsplit("/", 1)[-1]
    # Check mapping first
    for key, label in mapping.items():
        if key in fname:
            return label
    # Generic numbered assets (x1, x2, img1, etc.) → 方法示意图
    if re.match(r'^[a-z]+\d*$', fname):
        return "方法示意图"
    return fname[:40]


def generate_brief_entries(results: list[dict], date_str: str = None) -> str:
    """Generate the brief.md content from analysis results."""
    today = date_str or date.today().isoformat()
    lines = [f"# 资讯简报  {today}\n"]
    lines.append("")

    # Group by match level (skip not_interested)
    groups = {
        "interested": ("## [感兴趣]", "## [感兴趣]"),
        "possibly_interested": ("## [可能感兴趣]", "## [可能感兴趣 — 部分匹配/主题相关]"),
    }

    for level in ["interested", "possibly_interested"]:
        items = [r for r in results if r["match_level"] == level]
        if not items:
            continue

        title, _ = groups[level]
        lines.append(title)
        lines.append("")

        # Group items by source file
        file_groups = defaultdict(list)
        for item in items:
            file_groups[item["file"].name].append(item)

        for fname, file_items in file_groups.items():
            if len(file_items) > 1:
                # Multiple items from one file
                lines.append(f"### {fname}")
                lines.append(f"  ↳ 包含 {len(file_items)} 条资讯\n")

            for idx, item in enumerate(file_items, 1):
                if len(file_items) > 1:
                    entries_title = f"{fname} — 条目 {idx}: {item['title']}"
                else:
                    entries_title = item['title'] or fname

                lines.append(f"#### {entries_title}")
                lines.append(f"- 来源: {item['source_url']}")
                if date_str:
                    src_path = f"raw/digest/sources/{date_str}/{fname}"
                    lines.append(f"- 源文件: [{src_path}](/{src_path})")
                if item.get('title_cn'):
                    lines.append(f"- 标题: {item['title_cn']}")
                if item.get('domain'):
                    lines.append(f"- 领域: {item['domain']}")
                if item.get('keywords'):
                    kw = ', '.join(item['keywords']) if isinstance(item['keywords'], list) else item['keywords']
                    lines.append(f"- 关键词: {kw}")
                lines.append(f"- 匹配: {', '.join(item['matched_interests']) if item['matched_interests'] else '无'}")
                lines.append(f"- 理由: {item['reason']}")
                lines.append(f"- [ ] 深度阅读")
                lines.append(f"- [ ] 合入 wiki")
                lines.append(f"- [ ] 不感兴趣")
                lines.append("")

                # Figure / framework diagram
                fig_url, fig_short, fig_full = _extract_figure_from_source(item, source_url=item.get("source_url", ""))
                if fig_url:
                    lines.append(f"![{fig_short}]({fig_url})")
                    lines.append(f"**{fig_short}**")
                    lines.append(fig_full)
                    lines.append("")

                lines.append(f"**简介**：{item['brief']}")
                lines.append("")
                lines.append(f"**详细报告**（主要思路与方法流程）：")
                lines.append(item['detailed_report'])
                lines.append("")

    return "\n".join(lines)


def archive_current_brief():
    """Archive current brief.md to digest/brief/YYYY-MM-DD.md if it exists.
    Uses the date from the brief.md header (e.g. '# 资讯简报  2026-07-28')
    rather than date.today(), so archive filenames match the brief's actual date.
    """
    if not BRIEF_FILE.exists():
        return
    
    # Extract date from brief.md header
    content = read_file(BRIEF_FILE)
    date_match = re.search(r'# .*?(\d{4}-\d{2}-\d{2})', content)
    today = date_match.group(1) if date_match else date.today().isoformat()
    
    archive_path = BRIEF_DIR / f"{today}.md"
    if archive_path.exists():
        existing = read_file(BRIEF_FILE)
        archive_content = read_file(archive_path)
        archive_content += "\n\n---\n\n" + existing + f"\n\n**归档于: {today}**"
        write_file(archive_path, archive_content)
    else:
        shutil.copy2(str(BRIEF_FILE), str(archive_path))


def generate_new_brief():
    """After archiving, create a minimal brief.md placeholder for today.
    Uses the same date from the archived brief if available.
    """
    # Try to get date from archived brief
    today = date.today().isoformat()
    if BRIEF_DIR.exists():
        archives = sorted(BRIEF_DIR.glob("*.md"))
        if archives:
            m = re.search(r'(\d{4}-\d{2}-\d{2})', archives[-1].stem)
            if m:
                today = m.group(1)
    content = f"""# 资讯简报

---

## 今日暂无待处理资讯

---

## 操作指引

- 勾选「深度阅读」后，告诉 agent 生成详细解读
- 勾选「合入 wiki」后，告诉 agent 执行合入
- 勾选「不感兴趣」后，运行 deep-read 自动生成兴趣列表更新建议

## 状态说明

- **待处理**：已筛选，待确认
- **已深度阅读**：已生成深度阅读报告
- **已合入**：已合并到 wiki
- **已跳过**：用户选择不处理

"""
    write_file(BRIEF_FILE, content)


def move_source(file_path: Path, date_str: str):
    """Move .md file + its images/ dir to digest/sources/YYYY-MM-DD/."""
    dest_dir = DIGEST_DIR / "sources" / date_str
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_md = dest_dir / file_path.name

    if not dest_md.exists():
        shutil.move(str(file_path), str(dest_md))

    images_src = file_path.parent / "images"
    if images_src.exists():
        dest_images = dest_dir / "images"
        if not dest_images.exists():
            shutil.copytree(str(images_src), str(dest_images))

    return dest_md


def clear_inbox(skip_rel_paths: set[str] | None = None):
    """Clear inbox/ directory (keep inbox.md, empty its content). Keep files in skip_rel_paths."""
    if not INBOX_DIR.exists():
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
    inbox_files = list(INBOX_DIR.iterdir())
    if not inbox_files:
        # Ensure inbox.md exists even if dir is empty
        inbox_md = INBOX_DIR / "inbox.md"
        if not inbox_md.exists():
            inbox_md.write_text("# Inbox\n\n- \n", encoding="utf-8")
        print("  inbox/ 已为空。")
        return

    skipped = set()
    if skip_rel_paths:
        # convert rel paths to just filenames for comparison
        skipped = {Path(p).name for p in skip_rel_paths}

    count = 0
    for f in inbox_files:
        if f.name == "inbox.md":
            f.write_text("# Inbox\n\n- \n", encoding="utf-8")
            print("  📝 清空 inbox.md 内容")
            continue
        if f.name in skipped:
            print(f"  ⏭️  跳过失败文件: {f.name}")
            continue
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)
        count += 1
    if count:
        print(f"  ✅ 已清空 inbox/ ({count} 个文件)")

    # Ensure inbox.md exists
    inbox_md_path = INBOX_DIR / "inbox.md"
    if not inbox_md_path.exists() or not inbox_md_path.read_text(encoding="utf-8").strip():
        inbox_md_path.write_text("# Inbox\n\n- \n", encoding="utf-8")


def append_log(entry: str):
    existing = read_file(LOG_FILE)
    write_file(LOG_FILE, entry.strip() + "\n\n" + existing)


# ─── Checkpoint cache ──────────────────────────────────────────────

def load_filter_cache() -> dict:
    """Load per-file results cache. Returns {rel_path_str: [result_dict, ...]}."""
    if FILTER_CACHE.exists():
        try:
            return json.loads(FILTER_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_filter_cache(cache: dict):
    """Write cache to disk immediately."""
    FILTER_CACHE.parent.mkdir(parents=True, exist_ok=True)
    FILTER_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def rebuild_results_from_cache(cache: dict) -> list[dict]:
    """Rebuild results list from cache, skipping fallback/failed entries."""
    results = []
    for rel_path, entries in cache.items():
        abs_path = (REPO_ROOT / rel_path).resolve()
        for entry in entries:
            # Skip cached failed entries — they'll be retried next time
            if "LLM failed" in entry.get("reason", ""):
                continue
            entry["file"] = abs_path
            results.append(entry)
    return results


def build_brief_from_json(results_json_path: str, dry_run: bool = False):
    """Build brief.md from pre-analyzed results JSON (no LLM calls).

    Results JSON is a list of dicts produced by subagent analysis.
    This handles archiving, brief generation, file moving, and inbox cleanup.
    """
    results_path = Path(results_json_path)
    if not results_path.exists():
        print(f"❌ 结果文件不存在: {results_path}")
        sys.exit(1)

    raw = results_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        data = [data]

    # Reconstruct result dicts in the format expected by generate_brief_entries
    results = []
    failed_files: set[str] = set()
    for entry in data:
        file_path = entry.get("file", "")
        if isinstance(file_path, str):
            abs_path = (REPO_ROOT / file_path).resolve()
        else:
            abs_path = file_path

        if not abs_path.exists():
            print(f"  ⚠️  文件不存在: {abs_path}")

        results.append({
            "file": abs_path,
            "match_level": entry.get("match_level", "not_interested"),
            "matched_interests": entry.get("matched_interests", []),
            "reason": entry.get("reason", ""),
            "suggested_category": entry.get("suggested_category", "papers"),
            "title": entry.get("title", abs_path.stem),
            "title_cn": entry.get("title_cn", ""),
            "brief": entry.get("brief", ""),
            "detailed_report": entry.get("detailed_report", ""),
            "source_url": entry.get("source_url", ""),
            "figure_url": entry.get("figure_url", ""),
            "figure_caption": entry.get("figure_caption", ""),
            "domain": entry.get("domain", ""),
            "keywords": entry.get("keywords", []),
            "suggested_new_interests": entry.get("suggested_new_interests", []),
            "suggested_new_disinterests": entry.get("suggested_new_disinterests", []),
        })

    # Count stats
    interested = [r for r in results if r["match_level"] == "interested"]
    possibly = [r for r in results if r["match_level"] == "possibly_interested"]
    not_interested = [r for r in results if r["match_level"] == "not_interested"]
    print(f"📊 结果: {len(interested)} 感兴趣, {len(possibly)} 可能感兴趣, {len(not_interested)} 不感兴趣")

    # Collect suggestions
    suggested_interests = []
    suggested_disinterests = []
    seen_interest_names = set()
    seen_disinterest_names = set()
    for r in results:
        for si in r.get("suggested_new_interests", []):
            if isinstance(si, str):
                name = si
            else:
                name = si.get("name", "")
            if name and name not in seen_interest_names:
                seen_interest_names.add(name)
                suggested_interests.append(si)
        for sd in r.get("suggested_new_disinterests", []):
            if isinstance(sd, str):
                name = sd
            else:
                name = sd.get("name", "")
            if name and name not in seen_disinterest_names:
                seen_disinterest_names.add(name)
                suggested_disinterests.append(sd)

    # Detect source date from actual file paths rather than date.today()
    sources_dir = DIGEST_DIR / "sources"
    source_date = date.today().isoformat()
    for item in results:
        fp = item.get("file")
        if isinstance(fp, Path):
            m = re.search(r'(\d{4}-\d{2}-\d{2})', str(fp.parent))
            if m:
                source_date = m.group(1)
                break
    
    today = source_date
    new_entries = generate_brief_entries(results, today)

    if not dry_run:
        # Archive old brief
        archive_current_brief()

        # Write new brief
        write_file(BRIEF_FILE, new_entries)
        print(f"📝 简报已写入: {BRIEF_FILE.relative_to(REPO_ROOT)}")

        # Move source files
        for item in results:
            fp = item["file"]
            if isinstance(fp, Path) and fp.exists():
                try:
                    source_dest = move_source(fp, today)
                    print(f"  📦 {fp.name} → {source_dest.relative_to(REPO_ROOT)}")
                except Exception as e:
                    print(f"  ⚠️  move failed for {fp.name}: {e}")

        # Clear inbox
        clear_inbox(skip_rel_paths=failed_files)
        print("  🧹 inbox/ 已清空")

    # Print suggestions
    if suggested_interests:
        print("\n💡 建议新增兴趣点:")
        for si in suggested_interests:
            name = si if isinstance(si, str) else si.get("name", "")
            kw = name if isinstance(si, str) else ", ".join(si.get("keywords", []))
            weight = "0.5" if isinstance(si, str) else str(si.get("weight", 0.5))
            print(f"  - {name} (权重: {weight}) [{kw}]")
    if suggested_disinterests:
        print("\n🚫 建议新增排除项:")
        for sd in suggested_disinterests:
            name = sd if isinstance(sd, str) else sd.get("name", "")
            kw = name if isinstance(sd, str) else ", ".join(sd.get("keywords", []))
            weight = "0.9" if isinstance(sd, str) else str(sd.get("weight", 0.9))
            print(f"  - {name} (权重: {weight}) [{kw}]")

    # Auto-apply suggestions if --apply-suggestions
    if '--apply-suggestions' in sys.argv and (suggested_interests or suggested_disinterests):
        _apply_suggestions(suggested_interests, suggested_disinterests, log=print)

    # Log
    brief_count = len([r for r in results if r["match_level"] != "not_interested"])
    log_entry = f"## [{today}] filter | {len(results)} files processed"
    append_log(log_entry)
    print(f"\n✅ 筛选完成！简报: {BRIEF_FILE.relative_to(REPO_ROOT)}")
    """Main filter flow with per-file checkpoint cache."""
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    files = []
    for f in INBOX_DIR.rglob("*"):
        if f.name == "inbox.md":
            continue
        if f.is_file() and f.suffix.lower() in {".md", ".pdf", ".txt", ".html", ".docx", ".pptx", ".xlsx"}:
            files.append(f)
    files.sort()

    if not files:
        print("inbox/ 中没有可筛选的文件。")
        # Load cache and check if there were previously processed files
        if FILTER_CACHE.exists():
            cache = load_filter_cache()
            if cache:
                print("但有缓存中的历史结果。运行 --no-scan? 或用 --clear-cache 重置。")
        return

    print(f"找到 {len(files)} 个文件待筛选。\n")

    # Read interests/disinterests from interests.md
    all_entries = []
    interests_content = read_file(INTERESTS_FILE)
    if interests_content:
        all_entries = parse_interests(interests_content)
        print(f"读取到 {len(all_entries)} 个配置条目。\n")
        interests = [i for i in all_entries if i.get("category") != "排除列表"]
        disinterests = [i for i in all_entries if i.get("category") == "排除列表"]
        print(f"  兴趣点: {len(interests)}, 排除项: {len(disinterests)}\n")
    else:
        print("  提示：wiki/interests.md 为空，仅生成摘要不匹配兴趣。\n")
        interests = []
        disinterests = []

    # Load checkpoint cache
    cache = load_filter_cache()
    skipped_from_cache = 0

    # Precompile interests_desc (same for all files)
    interests_desc = ""
    for interest in interests:
        kw_str = ", ".join(interest.get("keywords", []))
        interests_desc += f"- {interest['name']}:\n  - 权重: {interest.get('weight', 0.5)}\n  - 关键词: [{kw_str}]\n  - 描述: {interest.get('description', '')}\n"

    # Precompile disinterests_desc
    disinterests_desc = ""
    for d in disinterests:
        kw_str = ", ".join(d.get("keywords", []))
        subcat = d.get("subcategory", "")
        subcat_prefix = f"[{subcat}] " if subcat else ""
        disinterests_desc += f"- {subcat_prefix}{d['name']}:\n  - 关键词: [{kw_str}]\n  - 描述: {d.get('description', '')}\n"

    # Collect files that need analysis
    pending = []
    for file_path in files:
        rel = str(file_path.relative_to(REPO_ROOT))
        if rel in cache:
            skipped_from_cache += 1
            n = len(cache[rel])
            print(f"  ⏭️  {file_path.name} ({n} 条，已缓存)")
        else:
            pending.append((file_path, rel))

    failed_files: set[str] = set()  # track failed rel paths

    # ── Pre-filter: skip files matching exclusion list (no LLM call) ──
    skipped_disinterest = 0
    if disinterests:
        disinterest_keywords_pre = set()
        for d in disinterests:
            disinterest_keywords_pre.update(k.lower() for k in d.get("keywords", []))
        if disinterest_keywords_pre:
            filtered_pending = []
            for fp, rel in pending:
                # Check filename first (cheap)
                target = fp.stem.lower().replace('-', ' ').replace('_', ' ')
                # Also check content head (first 500 chars)
                try:
                    head = read_file(fp)[:500].lower()
                    target += " " + head
                except Exception:
                    pass
                if any(re.search(r'\b' + re.escape(kw) + r'\b', target) for kw in disinterest_keywords_pre):
                    # Skip LLM entirely: create minimal result
                    serialized = [{
                        "file": rel,
                        "item_id": 1,
                        "match_level": "not_interested",
                        "matched_interests": [],
                        "reason": "匹配排除列表，跳过 LLM 分析。",
                        "suggested_category": "papers",
                        "title": fp.stem,
                        "title_cn": "",
                        "brief": "匹配排除列表，跳过。",
                        "detailed_report": "",
                        "source_url": extract_source_url(fp),
                        "domain": "",
                        "keywords": [],
                        "suggested_new_interests": [],
                        "suggested_new_disinterests": [],
                    }]
                    cache[rel] = serialized
                    save_filter_cache(cache)
                    skipped_disinterest += 1
                    print(f"  ⏭️  {fp.name} (排除列表命中, 跳过 LLM)")
                else:
                    filtered_pending.append((fp, rel))
            pending = filtered_pending

    if pending:
        print(f"\n需分析 {len(pending)} 个文件:\n")

        # ── Phase 1: write prompts to files for subagents ──
        if "--phase1" in sys.argv:
            tasks = []
            for fp, rel in pending:
                prompt = build_analyze_prompt(fp, interests_desc, disinterests_desc)
                tasks.append({
                    "id": rel.replace("/", "_").replace("\\", "_"),
                    "prompt": prompt,
                    "max_tokens": 4096,
                    "metadata": {"file": rel, "title": fp.stem},
                })
            prepare_tasks(tasks)
            return

        # ── Phase 2: read results from subagents ──
        if "--phase2" in sys.argv:
            results_map = read_results()
            print(f"📥 读取 {len(results_map)} 个结果")
            for fp, rel in pending:
                tid = rel.replace("/", "_").replace("\\", "_")
                raw = results_map.get(tid, "")
                if not raw:
                    print(f"  ⚠️  {fp.name}: 无结果")
                    failed_files.add(rel)
                    continue
                try:
                    file_results = parse_analyze_response(raw, fp, extract_source_url(fp))
                    serialized = []
                    for r in file_results:
                        item = dict(r)
                        item["file"] = rel
                        serialized.append(item)
                    cache[rel] = serialized
                    save_filter_cache(cache)
                    for r in file_results:
                        print(f"    → {r['file'].name}: {r['match_level']} ({r['suggested_category']})")
                except Exception as e:
                    print(f"  ⚠️  {fp.name} parse failed: {e}")
                    failed_files.add(rel)
            clean_task_dirs()
        else:
            # Normal mode: direct LLM calls
            with ThreadPoolExecutor(max_workers=2) as exec:
                future_map = {
                    exec.submit(analyze_file, fp, interests_desc, disinterests_desc): (fp, rel)
                    for fp, rel in pending
                }

                for future in as_completed(future_map):
                    fp, rel = future_map[future]
                    try:
                        file_results = future.result()
                        serialized = []
                        for r in file_results:
                            item = dict(r)
                            item["file"] = rel
                            serialized.append(item)
                        cache[rel] = serialized
                        save_filter_cache(cache)
                        for r in file_results:
                            print(f"    → {r['file'].name}: {r['match_level']} ({r['suggested_category']})")
                    except Exception as e:
                        print(f"  ⚠️  {fp.name} failed: {e}")
                        failed_files.add(rel)
    else:
        print(f"\n所有文件均已缓存（{skipped_from_cache} 个）。")

    # Rebuild full results from cache (skips cached failures)
    results = rebuild_results_from_cache(cache)

    # Post-process: apply disinterest exclusion rules
    disinterested_count = skipped_disinterest
    disinterest_keywords = set()
    for d in disinterests:
        disinterest_keywords.update(k.lower() for k in d.get("keywords", []))
    if disinterest_keywords:
        for r in results:
            if r["match_level"] == "not_interested":
                continue  # already caught by pre-filter
            target_text = " ".join([
                r.get("title", ""),
                r.get("title_cn", ""),
                r.get("domain", ""),
                " ".join(r.get("keywords", [])),
            ]).lower()
            if any(kw in target_text for kw in disinterest_keywords):
                r["match_level"] = "not_interested"
                r["matched_interests"] = []
                r["brief"] = "匹配排除列表，跳过。"
                r["detailed_report"] = ""
                disinterested_count += 1

    # Collect LLM-suggested new interests/disinterests
    suggested_interests = []
    suggested_disinterests = []
    seen_interest_names = set()
    seen_disinterest_names = set()
    for r in results:
        for si in r.get("suggested_new_interests", []):
            name = si.get("name", "")
            if name and name not in seen_interest_names:
                seen_interest_names.add(name)
                suggested_interests.append(si)
        for sd in r.get("suggested_new_disinterests", []):
            name = sd.get("name", "")
            if name and name not in seen_disinterest_names:
                seen_disinterest_names.add(name)
                suggested_disinterests.append(sd)

    # Inject source URL into each file's frontmatter before moving
    injected = set()
    for r in results:
        fp = r['file']
        if fp not in injected and r.get('source_url'):
            inject_source_url(fp, r['source_url'])
            injected.add(fp)

    # Sort: interested > possibly_interested > not_interested
    priority = {"interested": 0, "possibly_interested": 1, "not_interested": 2}
    results.sort(key=lambda x: priority.get(x["match_level"], 3))

    # Generate new entries markdown
    today = date.today().isoformat()
    new_entries = generate_brief_entries(results, today)

    if not dry_run:
        if BRIEF_FILE.exists() and BRIEF_FILE.stat().st_size > 50:
            existing = read_file(BRIEF_FILE)
            # Extract existing source_urls for dedup
            existing_urls = set(re.findall(r'^\- 来源: (.+)$', existing, re.MULTILINE))
            # Split new entries into individual items (by #### header)
            items = re.split(r'(?=^#### )', new_entries, flags=re.MULTILINE)
            to_append = []
            for item in items:
                m = re.search(r'^\- 来源: (.+)$', item, re.MULTILINE)
                if m and m.group(1) not in existing_urls:
                    to_append.append(item)
            if to_append:
                # Update date in header
                updated = re.sub(r'^# 资讯简报  \d{4}-\d{2}-\d{2}', f'# 资讯简报  {today}', existing)
                merged = updated.rstrip() + "\n\n" + "\n".join(to_append) + "\n"
                write_file(BRIEF_FILE, merged)
                print(f"  追加 {len(to_append)} 条新条目到 brief.md")
            else:
                print("  无新条目（全部已存在）")
                # Still update date if needed
                existing = re.sub(r'^# 资讯简报  \d{4}-\d{2}-\d{2}', f'# 资讯简报  {today}', existing)
                if existing != read_file(BRIEF_FILE):
                    write_file(BRIEF_FILE, existing)
        else:
            write_file(BRIEF_FILE, new_entries)

        for item in results:
            if item["file"].exists():
                print(f"  移动: {item['file'].name} → sources/{today}/")
                try:
                    source_dest = move_source(item["file"], today)
                    print(f"    ✅ {source_dest}")
                except Exception as e:
                    print(f"    ⚠️  move failed: {e}")

        clear_inbox(skip_rel_paths=failed_files)

        # Clear checkpoint cache
        if FILTER_CACHE.exists():
            FILTER_CACHE.unlink()
            print("  🧹 已清理缓存")

    # Log
    brief_count = len([r for r in results if r["match_level"] != "not_interested"])
    log_entry = f"## [{date.today().isoformat()}] filter | {len(results)} files processed"
    if disinterested_count:
        log_entry += f" ({disinterested_count} excluded)"
    if failed_files:
        log_entry += f" ({len(failed_files)} failed)"
    append_log(log_entry)

    if json_output:
        json_results = []
        for r in results:
            json_results.append({
                "file": str(r["file"].relative_to(REPO_ROOT)) if isinstance(r["file"], Path) else r["file"],
                "source_url": r["source_url"],
                "match_level": r["match_level"],
                "matched_interests": r["matched_interests"],
                "reason": r["reason"],
                "suggested_category": r["suggested_category"],
                "title": r["title"],
                "brief": r["brief"],
            })
        print(json.dumps(json_results, indent=2, ensure_ascii=False))
        return

    # Save failed files list for retry
    if failed_files:
        failed_paths = sorted(failed_files)
        failed_txt = REPO_ROOT / "raw" / ".filter-failed.txt"
        failed_txt.parent.mkdir(parents=True, exist_ok=True)
        content = "# 失败文件列表（LLM 连接错误）\n# 重跑: python tools/filter.py --retry-failed\n# {} files\n\n".format(len(failed_paths))
        content += "\n".join(failed_paths) + "\n"
        failed_txt.write_text(content, encoding="utf-8")
        print(f"\n⚠️ {len(failed_paths)} 个文件分析失败，已保存到 {failed_txt.relative_to(REPO_ROOT)}")

    # Print suggestions
    if suggested_interests:
        print("\n💡 建议新增兴趣点:")
        for si in suggested_interests:
            name = si if isinstance(si, str) else si.get("name", "")
            kw = name if isinstance(si, str) else ", ".join(si.get("keywords", []))
            weight = "0.5" if isinstance(si, str) else str(si.get("weight", 0.5))
            print(f"  - {name} (权重: {weight}) [{kw}]")
    if suggested_disinterests:
        print("\n🚫 建议新增排除项:")
        for sd in suggested_disinterests:
            name = sd if isinstance(sd, str) else sd.get("name", "")
            kw = name if isinstance(sd, str) else ", ".join(sd.get("keywords", []))
            weight = "0.9" if isinstance(sd, str) else str(sd.get("weight", 0.9))
            print(f"  - {name} (权重: {weight}) [{kw}]")
    if disinterested_count:
        print(f"\n  🚫 排除列表命中: {disinterested_count} 个文件未写入 brief")
    print(f"\n✅ 筛选完成！报告已保存到: {BRIEF_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and classify files in raw/inbox/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without moving files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--clear-cache", action="store_true", help="Clear checkpoint cache and re-analyze all files")
    parser.add_argument("--retry-failed", action="store_true", help="Re-process files listed in raw/.filter-failed.txt")
    parser.add_argument("--phase1", action="store_true", help="Write prompts to files for subagent processing")
    parser.add_argument("--phase2", action="store_true", help="Read results from subagent processing")
    parser.add_argument("--build-brief", type=str, metavar="RESULTS_JSON",
                        help="Build brief.md from pre-analyzed results JSON (skip LLM, do file mgmt)")
    parser.add_argument("--apply-suggestions", action="store_true",
                        help="Auto-apply suggested interests/disinterests to interests.md")
    args = parser.parse_args()

    if args.clear_cache:
        if FILTER_CACHE.exists():
            FILTER_CACHE.unlink()
            print("🧹 缓存已清理")
        else:
            print("缓存不存在，无需清理")
        sys.exit(0)

    if args.retry_failed:
        failed_file = REPO_ROOT / "raw" / ".filter-failed.txt"
        if not failed_file.exists():
            print("失败列表不存在: raw/.filter-failed.txt")
            sys.exit(1)
        lines = failed_file.read_text(encoding="utf-8").splitlines()
        paths = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
        if not paths:
            print("失败列表为空")
            sys.exit(0)
        moved = 0
        cache = load_filter_cache()
        for p in paths:
            src = (REPO_ROOT / p).resolve()
            cache.pop(p, None)
            if not src.exists():
                continue
            dst = (INBOX_DIR / src.name).resolve()
            if src == dst:
                continue  # already in inbox
            shutil.move(str(src), str(dst))
            moved += 1
        if moved or paths:
            save_filter_cache(cache)
            print(f"已清除 {len(paths)} 个缓存条目，移动 {moved} 个文件到 inbox/")
        os.remove(str(failed_file))
        print()

    if args.retry_failed or args.clear_cache:
        # Force fresh analysis
        pass  # run_filter handles both cases

    if args.build_brief:
        build_brief_from_json(args.build_brief)
        sys.exit(0)

    run_filter(dry_run=args.dry_run, json_output=args.json)
