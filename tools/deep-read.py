#!/usr/bin/env python3
"""
Generate deep-dive reading reports for selected files, and analyze disinterested entries.

Usage:
    python tools/deep-read.py              # process all checked in brief.md
    python tools/deep-read.py --date YYYY-MM-DD  # process specific date
    python tools/deep-read.py --file filename.md  # process single file

Flow:
    1. Read raw/digest/brief.md
    2a. Find entries marked "[x] 不感兴趣" → generate interests.md update suggestions
    2b. Find entries marked "[x] 深度阅读" → generate deep-dive report
    3. Accumulate reports by date, save as raw/digest/YYYY-MM-DD/deepdive.md
    4. Images go to deepdive/ directory, prefixed by entry slug
    5. Save disinterest suggestions as raw/digest/YYYY-MM-DD/disinterest-suggestions.md

Output:
    - raw/digest/YYYY-MM-DD/deepdive.md              — combined deep-dive report
    - raw/digest/YYYY-MM-DD/deepdive/                — images
    - raw/digest/YYYY-MM-DD/disinterest-suggestions.md — interests update suggestions
"""

import re
import sys
import json
import shutil
import argparse
import requests
from pathlib import Path
from datetime import date
from collections import defaultdict
import os

from _utils import read_file, write_file, call_llm, prepare_tasks, read_results, clean_task_dirs, TASK_DIR, rename_file_by_title

REPO_ROOT = Path(__file__).parent.parent
DAILY_DIR = REPO_ROOT / "raw" / "digest"
BRIEF_FILE = DAILY_DIR / "brief.md"
MAX_IMAGE_SIZE = 2 * 1024 * 1024

# Category directories to search for source files after ingest moves them out of sources/
CATEGORY_DIRS: list[Path] = []
raw_dir = REPO_ROOT / "raw"
if raw_dir.exists():
    CATEGORY_DIRS = [d for d in raw_dir.iterdir()
                     if d.is_dir() and d.name not in (".tmp", "digest", "inbox", "codes")]


def _find_source_file(entry: dict, today: str) -> tuple[Path | None, str | None]:
    """Find the source file for a brief entry.
    
    Search order:
    1. entry['source_path'] (as recorded in brief.md)
    2. digest/sources/<today>/ directory
    3. All raw/<category>/ directories (after ingest moved the file)
    4. Re-fetch from source_url
    """
    source_date = None
    
    if entry.get('source_path'):
        candidate = (REPO_ROOT / entry['source_path']).resolve()
        if candidate.exists():
            m = re.search(r'(\d{4}-\d{2}-\d{2})', str(candidate))
            source_date = m.group(1) if m else None
            return candidate, source_date
    
    sources_dir = DAILY_DIR / "sources" / today
    title = entry.get('title', '')
    if sources_dir.exists():
        for f in sources_dir.iterdir():
            if title in f.name or f.name.startswith(title.split('.')[0]):
                return f, today
    
    for cat_dir in CATEGORY_DIRS:
        if not cat_dir.exists():
            continue
        for f in cat_dir.iterdir():
            if f.suffix != '.md':
                continue
            if title in f.name or f.name.startswith(title.split('.')[0]):
                return f, None
    
    if entry.get('source_url'):
        tmp_dir = DAILY_DIR / "deepdive" / today / ".tmp"
        tmp_fetched = refetch_source(entry['source_url'], tmp_dir)
        if tmp_fetched and tmp_fetched.exists():
            return tmp_fetched, today
    
    return None, None

ARXIV_PATTERNS = [
    re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"arxiv\.org/pdf/(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$"),
]


def extract_arxiv_id(text: str) -> str | None:
    for p in ARXIV_PATTERNS:
        m = p.search(text)
        if m:
            return m.group(1)
    return None


def refetch_source(source_url: str, tmp_dir: Path) -> Path | None:
    """Re-fetch source content from URL. Save to tmp_dir, return path or None."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    arxiv_id = extract_arxiv_id(source_url)

    if arxiv_id:
        return _refetch_arxiv(arxiv_id, tmp_dir)
    elif source_url.startswith("http"):
        return _refetch_web(source_url, tmp_dir)
    return None


def _refetch_arxiv(arxiv_id: str, tmp_dir: Path) -> Path | None:
    """Re-fetch arXiv paper content."""
    out_file = tmp_dir / f"arxiv-{arxiv_id}.md"
    if out_file.exists():
        # Check if there's already a title-based rename
        for f in tmp_dir.iterdir():
            if f.suffix == '.md' and f.stem != out_file.stem and arxiv_id not in f.stem:
                return f  # already renamed
        return out_file

    try:
        from arxiv2md import ingest_paper_sync
        result = ingest_paper_sync(arxiv_id)
        content = re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', result.content)
        out_file.write_text(content, encoding="utf-8")
        # Rename to title-based slug for readability
        renamed = rename_file_by_title(out_file)
        return renamed
    except ImportError:
        pass
    finally:
        cache_dir = REPO_ROOT / ".arxiv2md_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)

    # Fallback: fetch abstract from arXiv API
    try:
        import requests
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        import xml.etree.ElementTree as ET
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.content)
        entry = root.find("atom:entry", ns)
        if entry is not None:
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ").replace("  ", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ").replace("  ", " ")
            content = f"""# {title}

**arXiv**: https://arxiv.org/abs/{arxiv_id}

**Abstract**:
{summary}
"""
            out_file.write_text(content, encoding="utf-8")
            renamed = rename_file_by_title(out_file)
            return renamed
    except Exception:
        pass

    out_file.write_text(f"# arXiv: {arxiv_id}\n\n[Unable to re-fetch content]\n\nOriginal: https://arxiv.org/abs/{arxiv_id}\n", encoding="utf-8")
    out_file_renamed = rename_file_by_title(out_file)
    return out_file_renamed


def _refetch_web(url: str, tmp_dir: Path) -> Path | None:
    """Re-fetch web page content."""
    import hashlib
    slug = hashlib.md5(url.encode()).hexdigest()[:12]
    out_file = tmp_dir / f"web-{slug}.md"
    if out_file.exists():
        return out_file

    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'

        # Extract title
        title = ""
        m = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()

        try:
            import trafilatura
            md = trafilatura.extract(resp.text, include_comments=False, include_tables=True) or ""
        except ImportError:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                md = soup.get_text(separator="\n", strip=True)
            except ImportError:
                md = resp.text[:10000]

        content = f"# {title or 'Untitled'}\n\n{md}\n\n原始链接: {url}\n"
        out_file.write_text(content, encoding="utf-8")
        if title:
            renamed = rename_file_by_title(out_file)
            return renamed
        return out_file
    except Exception as e:
        out_file.write_text(f"# Error: {url}\n\n{e}\n", encoding="utf-8")
        return out_file


def extract_images(content):
    """Extract (alt_text, url, context_2lines) from markdown source."""
    pattern = re.compile(r'!\[(.*?)\]\((\S+?)\)')
    results = []
    lines = content.split('\n')
    for i, line in enumerate(lines):
        for m in pattern.finditer(line):
            alt = m.group(1)
            url = m.group(2)
            ctx_start = max(0, i - 2)
            ctx = '\n'.join(lines[ctx_start:i])
            results.append((alt, url, ctx))
    return results


def download_images(images, dest_dir, prefix):
    """Download images to dest_dir/{prefix-fig1.ext, ...}. Returns list of (url, filename, alt)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for idx, (alt, url, ctx) in enumerate(images):
        ext = Path(url.split('?')[0]).suffix.lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
            ext = '.png'
        filename = f"{prefix}-fig{idx + 1}{ext}"
        try:
            resp = requests.get(url, headers=headers, timeout=15, stream=True)
            resp.raise_for_status()
            cl = int(resp.headers.get('content-length', 0))
            if cl > MAX_IMAGE_SIZE:
                continue
            data = resp.content
            if len(data) > MAX_IMAGE_SIZE:
                continue
            (dest_dir / filename).write_bytes(data)
            downloaded.append((url, filename, alt))
        except Exception:
            continue
    return downloaded


def build_image_prompt_section(downloaded, prefix):
    """Build image info block for LLM prompt. Empty string if no images."""
    if not downloaded:
        return ""
    first = f"images/{downloaded[0][1]}"  # first image, relative to .md files in deepdive/date/
    parts = ["\n---\n源文档中包含以下图片："]
    for url, filename, alt in downloaded:
        caption = alt if alt else '(无标题)'
        img_path = f"images/{filename}"
        parts.append(f"- `{img_path}` — {caption} ({url})")
    parts += [
        "",
        "请判断哪些是核心**算法图、架构图、流程图**等结构性图片。",
        f"在报告中用 `![图片标题]({first})` 等路径引用它们（相对于 .md 文件所在目录）。",
        "忽略非结构性的装饰图（如结果对比图、示例截图、数据集样本等）。",
    ]
    return "\n".join(parts)


def copy_local_images(images, source_dir, dest_dir, prefix):
    """Copy local images from source_dir to dest_dir with prefix.
    Returns list of (orig_path, filename, alt) for successful copies."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for idx, (alt, url, ctx) in enumerate(images):
        if url.startswith("http"):
            continue
        ext = Path(url.split('?')[0]).suffix.lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
            ext = '.png'
        filename = f"{prefix}-fig{idx + 1}{ext}"
        src = Path(source_dir) / url
        if src.exists():
            if src.stat().st_size > MAX_IMAGE_SIZE:
                continue
            dest = dest_dir / filename
            shutil.copy2(str(src), str(dest))
            copied.append((url, filename, alt))
    return copied


def cleanup_deepdive_images(report_content, image_dir):
    """Remove images in image_dir not referenced in combined deepdive.md."""
    if not image_dir or not image_dir.exists():
        return
    referenced = set()
    for m in re.finditer(r'\]\(([^)]+)\)', report_content):
        ref = m.group(1)
        if not ref.startswith("http") and '/' in ref:
            referenced.add(Path(ref).name)
    for f in image_dir.iterdir():
        if f.is_file() and f.name not in referenced:
            f.unlink()


def _parse_brief_entries(brief_content: str, date_str: str = None) -> list[dict]:
    """Parse brief.md into entry dicts with metadata (shared parser)."""
    HEADER = re.compile(r'^#{3,4} (.+)')
    entries = []
    lines = brief_content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]
        header_match = HEADER.match(line)
        if header_match and not line.lstrip().startswith('### ['):
            file_title = header_match.group(1).strip()

            if date_str:
                found_date = False
                for j in range(max(0, i-10), i):
                    if date_str in lines[j]:
                        found_date = True
                        break
                if not found_date:
                    i += 1
                    continue

            entry_lines = []
            next_i = i + 1
            while next_i < len(lines):
                if HEADER.match(lines[next_i]) and not lines[next_i].lstrip().startswith('### ['):
                    break
                entry_lines.append(lines[next_i])
                next_i += 1

            entry_text = '\n'.join(entry_lines)

            source_url = ''
            url_match = re.search(r'- 来源:\s*(.+)', entry_text)
            if url_match:
                source_url = url_match.group(1).strip()

            source_path = ''
            path_match = re.search(r'- 源文件:\s*(.+)', entry_text)
            if path_match:
                source_path = path_match.group(1).strip()

            brief = ''
            brief_match = re.search(r'\*\*简介\*\*：(.+?)(?=\*\*详细报告\*\*|\n\n|$)', entry_text, re.DOTALL)
            if brief_match:
                brief = brief_match.group(1).strip()

            has_deepread = bool(re.search(r'\[x\]\s*深度阅读|\[X\]\s*深度阅读', entry_text))
            has_disinterest = bool(re.search(r'\[x\]\s*不感兴趣|\[X\]\s*不感兴趣', entry_text))

            domain = ''
            dp = re.search(r'- 领域:\s*(.*)', entry_text)
            if dp: domain = dp.group(1).strip()

            keywords = ''
            kp = re.search(r'- 关键词:\s*(.*)', entry_text)
            if kp: keywords = kp.group(1).strip()

            matched = ''
            mp = re.search(r'- 匹配:\s*(.*)', entry_text)
            if mp: matched = mp.group(1).strip()

            reason = ''
            rp = re.search(r'- 理由:\s*(.*)', entry_text)
            if rp: reason = rp.group(1).strip()

            entries.append({
                'title': file_title,
                'source_url': source_url,
                'source_path': source_path,
                'domain': domain,
                'keywords': keywords,
                'matched_interests': matched,
                'reason': reason,
                'brief': brief,
                'entry_lines': entry_text,
                'has_deepread': has_deepread,
                'has_disinterest': has_disinterest,
            })

            i = next_i
        else:
            i += 1

    return entries


def find_checked_entries(brief_content: str, date_str: str = None) -> list[dict]:
    """Parse brief.md to find entries marked "[x] 深度阅读"."""
    all_entries = _parse_brief_entries(brief_content, date_str)
    entries = [e for e in all_entries if e['has_deepread']]
    for e in entries:
        e['deepdive_existed'] = 'deepdive' in e['entry_lines'].lower()
    return entries


def find_disinterested_entries(brief_content: str, date_str: str = None) -> list[dict]:
    """Parse brief.md to find entries marked "[x] 不感兴趣" (and not also deep-read)."""
    all_entries = _parse_brief_entries(brief_content, date_str)
    return [e for e in all_entries if e['has_disinterest'] and not e['has_deepread']]


def build_disinterest_suggestion_prompt(entry: dict) -> str:
    """Build prompt for disinterest suggestion with full context and element-level analysis."""
    title = entry['title']
    brief = entry['brief']
    domain = entry.get('domain', '?')
    keywords = entry.get('keywords', '?')
    matched = entry.get('matched_interests', '?')
    reason = entry.get('reason', '?')

    interests_md = Path(__file__).parent.parent / "wiki" / "interests.md"
    interests_content = interests_md.read_text(encoding="utf-8") if interests_md.exists() else "(not found)"

    return f"""你是一个兴趣管理系统分析助手。用户标记了对以下内容「不感兴趣」。

## 文档信息

- 标题: {title}
- 领域: {domain}
- 关键词: {keywords}
- 匹配到的兴趣: {matched}
- 匹配理由: {reason}
- 简介: {brief}

## 当前兴趣配置（wiki/interests.md）

{interests_content}

## 任务

用户标记此条目为「不感兴趣」。你需要做三件事：

### 1. 判定不感兴趣的元素（重要）

请分析该条目的哪些具体方面导致了用户不感兴趣。可能的原因包括（选择适用项）：

- **方向层面不感兴趣**：整个领域方向用户都不想关注（如「医学AI」）
- **子方向不感兴趣**：匹配到了用户的兴趣但具体子方向不感兴趣（如匹配了3DGS但论文是关于医学3DGS）
- **方法路线不感兴趣**：方向有兴趣，但这个方法路线不感兴趣（如用户只对3DGS感兴趣、不对NeRF感兴趣）
- **应用场景不感兴趣**：方向和方法都还行但应用场景不感兴趣（如游戏渲染 vs 科学可视化）
- **内容深度不够**：产品介绍/非技术文章，信息量不足
- **与兴趣关联太弱**：勉强匹配上但实质关联不大
- **其他/单次一次性**

### 2. 判断是否需要更新 interests.md

基于元素分析，决定是否需要修改 interests.md：

- **不需要**：文档确实与兴趣相关但只是单篇不感兴趣（属于个人偏好），不值得更改兴趣配置
- **需要新增排除项**：文档所属的整个子方向应该被排除

### 3. ⚠️ 不可违反的保护规则

**绝对禁止的操作：**
- ❌ **禁止建议删除、修改或移动任何现有兴趣条目**（如「3D高斯泼溅」无论什么情况都不能动）
- ❌ **禁止建议将现有兴趣移入排除列表**
- ❌ **禁止建议修改现有兴趣的关键词来「缩窄匹配」**

**允许的唯一操作：**
- ✅ **仅建议在排除列表下新增一个完整的子方向条目**（如 `### 移动端图形` → `- Arm神经渲染 [Arm, NSS, 移动端GPU超采样]`）
- ✅ 如果拿不准，选 `no_action`

**关键判断原则：「已有兴趣不会自动变成不感兴趣」— 不感兴趣的只可能是【从未被列为兴趣的新方向】。**

## 输出格式

返回 JSON（不要代码块/不要 markdown fences）：

{{
    "suggested_action": "add_disinterest | no_action",
    "interest_elements": ["方向层面不感兴趣", "方法路线不感兴趣"],
    "element_reasoning": "简要说明为什么这些元素导致不感兴趣",
    "disinterest_name": "建议新增的排除项名称（如果建议新增）",
    "disinterest_keywords": ["相关关键词"],
    "disinterest_description": "简要说明",
    "reasoning": "综合推理过程",
    "protects_interests": true,
    "protection_note": "此建议是否会影响现有兴趣？如何确保不损害已有配置？"
}}"""


def generate_disinterest_suggestion(entry: dict) -> dict:
    """Call LLM to suggest interests.md updates based on a disinterested entry."""
    title = entry['title']
    prompt = build_disinterest_suggestion_prompt(entry)

    try:
        raw = call_llm(prompt, max_tokens=1024)
        if not raw:
            print(f"  ⚠️ LLM 返回空（phase1 模式），跳过 disinterest 分析: {entry.get('title', '')[:50]}")
            return {
                'title': entry.get('title', ''),
                'suggested_action': 'no_action',
                'disinterest_name': '',
                'disinterest_keywords': [],
                'disinterest_description': '',
                'reasoning': 'LLM 返回空（phase1 模式）',
            }
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        clean = re.sub(r"\s*```$", "", clean.strip())
        result = json.loads(clean)
        result['title'] = title
        return result
    except Exception as e:
        return {
            'title': title,
            'suggested_action': 'no_action',
            'disinterest_name': '',
            'disinterest_keywords': [],
            'disinterest_description': '',
            'reasoning': f'LLM 调用失败: {e}',
        }


def build_deepdive_prompt(file_path: Path, title: str, brief: str,
                          prefix: str = "", downloaded_images: list = None,
                          source_url: str = "",
                          entry_lines: str = "") -> str:
    """Build the prompt for deep-dive report generation."""
    content = read_file(file_path)
    max_chars = int(os.environ.get("WIKI_MAX_CONTENT_CHARS", "20000"))
    if len(content) > max_chars:
        content = content[:max_chars]

    img_section = ""
    example_img = ""
    if downloaded_images:
        img_section = build_image_prompt_section(downloaded_images, prefix)
        example_img = f"images/{downloaded_images[0][1]}"

    return f"""深度阅读助手。分析文档，生成中文报告，包含完整的元数据区块和方法双重写作。

标题: {title}
简介: {brief}
{('来源链接: ' + source_url) if source_url else ''}

=== 文档内容 ===
{content}
=== END ===
{img_section}

报告结构要求：

## 元数据（放在报告最开头，使用列表格式）
- 论文标题: {title}
- 原始链接: [{'arXiv: ' + source_url.split('/abs/')[-1] if '/abs/' in source_url else source_url}]({source_url})（如有）
- 项目主页:（从文档中提取，如无可留空）
- 代码仓库:（从文档中提取，如无可留空）
- 对应 brief 条目: 来自 {BRIEF_FILE.name}，日期 {prefix.split('_')[0] if '_' in prefix else '?'}

## 论文概览（仅背景、贡献和指标，不要涉及方法细节）

1. **解决的问题** — 一句话
2. **现有方法不足** — 一句话  
3. **本文贡献** — 一句话
4. **效果指标** — 一句话

## 方法拆解（全部方法内容，这是报告主体）
   
### 整体思路（直白解释）
- 用通俗语言解释：**为什么这样做**、**每个步骤在干什么**
- 说清设计动机和直觉，让非专业读者也能理解

### 分步拆解
对每个算法/组件/公式，按顺序以步骤格式说明：

**步骤 N: [组件/公式名称]**
- **输入/目的**：输入什么，要解决什么问题
- **原理**：怎么做的（直觉解释，先说在干什么）
- **公式**：关键公式 + 符号含义 + 直觉
- **输出/效果**：输出什么，效果和对后续的影响
- **效果说明**：输出值大小或取值范围对后续步骤的影响

## 启示与思考
- 该工作的启发性、关键洞见
- 与已有知识的关联
- 未来方向建议
- 实践中的应用前景

要求：中文，**概览不涉及方法细节**，**方法拆解覆盖所有方法内容**。
用 `![描述]({example_img})` 引用核心架构图/流程图。
**重要：直接输出纯文本，不要用 ```markdown ``` 代码块包裹。**"""


def clean_report_section_titles(raw: str) -> str:
    """Strip parenthetical LLM instructions from section titles.
    
    E.g. '## 论文概览（仅背景、贡献和指标，不要涉及方法细节）' → '## 论文概览'
    """
    raw = re.sub(r'^(#{1,4}\s+.+?)[（(].*?[）)]', r'\1', raw, flags=re.MULTILINE)
    return raw


def generate_deepdive(file_path: Path, title: str, brief: str,
                      prefix: str = "", downloaded_images: list = None,
                      source_url: str = "") -> str:
    """Generate a 1500-3000 word deep-dive report for the file."""
    prompt = build_deepdive_prompt(file_path, title, brief, prefix, downloaded_images, source_url)
    try:
        raw = call_llm(prompt, max_tokens=8192)
        raw = re.sub(r"^```(?:markdown)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        raw = clean_report_section_titles(raw)
        return raw
    except Exception as e:
        return f"⚠️ 深度阅读生成失败：{e}"


def build_deepdive_from_summary_prompt(title: str, brief: str, detailed_report: str,
                                       source_url: str = "") -> str:
    """Build prompt for deep report from existing summary."""
    return f"""你是 AI 深度阅读助手。请基于以下文档信息，生成一份清晰易懂的深度阅读报告。

文档信息：
- 标题: {title}
- 已有简介: {brief}
- 已有详细报告: {detailed_report}
{('- 来源链接: ' + source_url) if source_url else ''}

报告结构要求：

## 元数据（放在报告最开头）
- 论文标题: {title}
- 原始链接: [{source_url}]({source_url})（如有）
- 项目主页:（从已有信息中提取，如无可留空）
- 代码仓库:（从已有信息中提取，如无可留空）
- 对应 brief 条目: 来自 brief.md

## 论文概览（仅背景、贡献、指标，不含方法细节）

用简洁语言回答以下 4 点（每项 1-2 句话）：

1. **解决的问题** — 一句话
2. **现有不足** — 一句话
3. **本文贡献** — 一句话
4. **效果** — 一句话

## 方法拆解（全部方法内容，这是报告主体）

### 整体思路（直白解释）
- 用通俗语言解释：**为什么这样做**、**每个步骤在干什么**
- 说清设计动机和直觉

### 分步拆解
对文档中涉及的算法/方法/公式，按顺序逐一展开：

**步骤 N: [算法/方法名称]**
- **输入/目的**：输入什么，解决什么问题
- **原理**：怎么做的（先解释在干什么，再说公式）
- **公式**：关键公式 + 符号含义 + 直觉
- **输出/效果**：输出什么，对后续的影响

## 启示与思考
- 该工作的启发性、关键洞见
- 与已有知识的关联
- 未来方向建议

整体要求：
- 中文
- **概览不涉及方法细节，方法拆解覆盖所有方法**
- 不要出现 [[wikilinks]] 格式
- **直接输出纯文本，不要用 ```markdown ``` 代码块包裹**"""


def generate_deepdive_from_summary(title: str, brief: str, detailed_report: str,
                                   source_url: str = "") -> str:
    """Generate deep report from existing summary and detailed report."""
    prompt = build_deepdive_from_summary_prompt(title, brief, detailed_report, source_url)
    try:
        raw = call_llm(prompt, max_tokens=8192)
        raw = re.sub(r"^```(?:markdown)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        raw = clean_report_section_titles(raw)
        return raw
    except Exception as e:
        return f"⚠️ 深度阅读生成失败：{e}"


def update_brief_status(brief_content: str, title_to_process: str) -> str:
    """Update brief.md: mark items as processed after deep-dive generation."""
    # Replace "[x] 深度阅读" with "[x] 已深度阅读" for processed items
    # This is a simple marker change to indicate completion

    lines = brief_content.split('\n')
    new_lines = []
    in_target_entry = False
    target_title = None

    for i, line in enumerate(lines):
        # Check surrounding lines for title (support ### or #### headers)
        if any(title_to_process in lines[j] for j in range(max(0, i-3), i+1)):
            pass

        # Simple approach: find "[x] 深度阅读" and if this is a target entry, mark it differently
        if '[x] 深度阅读' in line or '[X] 深度阅读' in line:
            # Check if we're at a target entry (look back for title)
            for j in range(max(0, i-20), i):
                if title_to_process in lines[j]:
                    in_target_entry = True
                    break
            if in_target_entry:
                line = line.replace('[x] 深度阅读', '[x] 已深度阅读').replace('[X] 深度阅读', '[X] 已深度阅读')

        new_lines.append(line)

    return '\n'.join(new_lines)


def run_deep_read(date_str: str = None, file_name: str = None, json_output: bool = False):
    """Main deep-read flow."""
    if not BRIEF_FILE.exists():
        print("brief.md not found. Run filter.py first.")
        return

    brief_content = read_file(BRIEF_FILE)

    # Detect the brief's date from its header (e.g. "# 资讯简报  2026-07-28")
    # rather than using date.today(), so archive/output files match the source date.
    brief_date_match = re.search(r'# .*?(\d{4}-\d{2}-\d{2})', brief_content)
    brief_date = brief_date_match.group(1) if brief_date_match else date.today().isoformat()

    # Find checked entries
    if date_str:
        entries = find_checked_entries(brief_content, date_str)
    elif file_name:
        # Find entry with this filename
        entries = []
        lines = brief_content.split('\n')
        HEADER = re.compile(r'^#{3,4} ')
        i = 0
        while i < len(lines):
            if file_name in lines[i] and HEADER.match(lines[i]):
                entry_lines = []
                next_i = i + 1
                while next_i < len(lines) and not HEADER.match(lines[next_i]):
                    entry_lines.append(lines[next_i])
                    next_i += 1

                entry_text = '\n'.join(entry_lines)
                if re.search(r'\[x\]\s*深度阅读|\[X\]\s*深度阅读', entry_text):
                    source_url = ''
                    url_match = re.search(r'- 来源:\s*(.+)', entry_text)
                    if url_match:
                        source_url = url_match.group(1).strip()
                    source_path = ''
                    path_match = re.search(r'- 源文件:\s*(.+)', entry_text)
                    if path_match:
                        source_path = path_match.group(1).strip()
                    brief = ''
                    brief_match = re.search(r'\*\*简介\*\*：(.+?)(?=\*\*详细报告\*\*|\n\n|$)', entry_text, re.DOTALL)
                    if brief_match:
                        brief = brief_match.group(1).strip()
                    entries.append({
                        'title': file_name,
                        'source_url': source_url,
                        'source_path': source_path,
                        'brief': brief,
                        'entry_lines': entry_text,
                        'deepdive_existed': False,
                    })
                i = next_i
            i += 1
    else:
        entries = find_checked_entries(brief_content)

    # ── Process disinterested entries (generate suggestion) ──
    disinterest_entries = []
    if not file_name:  # skip in --file mode
        if date_str:
            disinterest_entries = find_disinterested_entries(brief_content, date_str)
        else:
            disinterest_entries = find_disinterested_entries(brief_content)

    if disinterest_entries:

        if "--phase1" in sys.argv:
            # Phase 1: accumulate disinterest tasks; deep-read tasks will be added below
            _disinterest_tasks = []
            for de in disinterest_entries:
                prompt = build_disinterest_suggestion_prompt(de)
                _disinterest_tasks.append({
                    "id": f"disinterest_{de['title'][:30]}",
                    "prompt": prompt,
                    "max_tokens": 1024,
                    "metadata": {"title": de['title']},
                })

        if "--phase2" in sys.argv:
            # Phase 2: read results
            results_map = read_results()
            suggestions = []
            for de in disinterest_entries:
                tid = f"disinterest_{de['title'][:30]}"
                raw = results_map.get(tid, "")
                if raw:
                    try:
                        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip())
                        clean = re.sub(r"\s*```$", "", clean.strip())
                        result = json.loads(clean)
                        result['title'] = de['title']
                        suggestions.append(result)
                    except Exception:
                        suggestions.append({'title': de['title'], 'suggested_action': 'no_action'})
                else:
                    suggestions.append({'title': de['title'], 'suggested_action': 'no_action'})
            clean_task_dirs()
        else:
            # Normal mode: direct LLM calls
            suggestions = []
            for de in disinterest_entries:
                suggestion = generate_disinterest_suggestion(de)
                suggestions.append(suggestion)
                elements = suggestion.get('interest_elements', [])
                if elements:
                    print(f"    原因: {suggestion.get('element_reasoning', '')}")
                if suggestion.get('suggested_action') == 'add_disinterest':
                    kw = ', '.join(suggestion.get('disinterest_keywords', []))
                    name = suggestion.get('disinterest_name', '')
                    print(f"    理由: {suggestion.get('reasoning', '')}")
                print()

        if not json_output:
            today_str = date.today().isoformat()
            sug_path = DAILY_DIR / "deepdive" / today_str / "disinterest-suggestions.md"
            sug_path.parent.mkdir(parents=True, exist_ok=True)
            sug_line = f"# 不感兴趣条目分析建议  {today_str}\n"
            for s in suggestions:
                sug_line += f"## {s.get('title', '')}\n"
                elements = s.get('interest_elements', [])
                if elements:
                    sug_line += f"- 不感兴趣元素: {' + '.join(elements)}\n"
                    sug_line += f"- 元素原因: {s.get('element_reasoning', '')}\n"
                sug_line += f"- 建议操作: {s.get('suggested_action', '')}\n"
                sug_line += f"- 排除项名称: {s.get('disinterest_name', '')}\n"
                sug_line += f"- 关键词: {', '.join(s.get('disinterest_keywords', []))}\n"
                sug_line += f"- 是否保护现有兴趣: {s.get('protects_interests', 'unknown')}\n"
                sug_line += f"- 保护说明: {s.get('protection_note', '')}\n"
                sug_line += f"- 理由: {s.get('reasoning', '')}\n"
                sug_line += "\n"
            write_file(sug_path, sug_line)

    # ── Check for deep-read entries ──
    if not entries:
        if not disinterest_entries:
            return
        # If only disinterested entries, we're done
        return


    # Use brief_date from header (detected above in archive block) for all date-sensitive paths
    today = brief_date  # instead of date.today().isoformat() -- preserves source date

    # ── Phase 1: prepare tasks ──
    if "--phase1" in sys.argv:
        # Include any disinterest tasks accumulated above
        tasks = list(_disinterest_tasks) if '_disinterest_tasks' in dir() else []
        metadata_map = {}  # task_id -> metadata for phase2
        for entry in entries:
            title = entry['title']
            safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)

            # Dedup: skip if deepdive.md already has an entry with this title
            file_path, source_date = _find_source_file(entry, today)
            date_key = source_date or today
            existing_deepdive = DAILY_DIR / "deepdive" / date_key / "deepdive.md"
            if existing_deepdive.exists():
                existing_content = existing_deepdive.read_text(encoding="utf-8")
                # Match "## Title" header in deepdive.md
                existing_titles = re.findall(r'^## (.+)$', existing_content, re.MULTILINE)
                if any(title.strip() == t.strip() for t in existing_titles):
                    continue
            # Fallback: if deepdive.md doesn't have the title but standalone file exists
            if not existing_deepdive.exists():
                slug = safe_title.lower().replace('__', '-').replace('_', '-')
                standalone = DAILY_DIR / "deepdive" / date_key / f"{slug}.md"
                if standalone.exists():
                    continue

            # Prepare paths
            base_dir = DAILY_DIR / "deepdive" / date_key

            # Extract & download images
            downloaded_images = []
            if file_path and file_path.exists():
                content = read_file(file_path)
                all_imgs = extract_images(content)
                if all_imgs:
                    image_dir = base_dir / "images"
                    url_imgs = [(a, u, c) for a, u, c in all_imgs if u.startswith("http")]
                    local_imgs = [(a, u, c) for a, u, c in all_imgs if not u.startswith("http")]
                    if url_imgs:
                        dl = download_images(url_imgs, image_dir, safe_title)
                        downloaded_images.extend(dl)
                    if local_imgs:
                        sources_img_dir = file_path.parent / "images"
                        if sources_img_dir.exists():
                            cl = copy_local_images(local_imgs, sources_img_dir, image_dir, safe_title)
                            downloaded_images.extend(cl)

            # Build prompt
            if file_path and file_path.exists():
                prompt = build_deepdive_prompt(file_path, title, entry['brief'],
                                               prefix=safe_title, downloaded_images=downloaded_images,
                                               source_url=entry.get('source_url', ''),
                                               entry_lines=entry.get('entry_lines', ''))
            else:
                detailed_report = ''
                detailed_match = re.search(r'\*\*详细报告\*\*：(.+?)(?=\n\n|\n###|$)', entry['entry_lines'], re.DOTALL)
                if detailed_match:
                    detailed_report = detailed_match.group(1).strip()
                prompt = build_deepdive_from_summary_prompt(title, entry['brief'], detailed_report)

            tid = f"deepdive_{safe_title}"
            tasks.append({
                "id": tid,
                "prompt": prompt,
                "max_tokens": 8192,
                "metadata": {"title": title, "date_key": date_key, "safe_title": safe_title},
            })

        prepare_tasks(tasks)
        return

    # ── Phase 2: read results ──
    if "--phase2" in sys.argv:
        results_map = read_results()
        by_date = defaultdict(list)
        for entry in entries:
            title = entry['title']
            safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
            tid = f"deepdive_{safe_title}"

            # Get metadata from task file
            task_file = TASK_DIR / f"{tid}.json"
            if task_file.exists():
                task_data = json.loads(task_file.read_text(encoding="utf-8"))
                date_key = task_data.get("metadata", {}).get("date_key", today)
            else:
                date_key = today

            raw = results_map.get(tid, "")
            if raw:
                raw = re.sub(r"^```(?:markdown)?\s*", "", raw.strip())
                raw = re.sub(r"\s*```$", "", raw.strip())
                by_date[date_key].append((safe_title, raw, None, title))
            else:
                by_date[date_key].append((safe_title, f"⚠️ 无结果", None, title))

        clean_task_dirs()
    else:
        # Normal mode: use existing phase1 logic to prepare tasks, then return
        # Jump to phase1 logic by re-executing the phase1 block
        _phase1_tasks = []
        for entry in entries:
            title = entry['title']
            safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
            file_path, source_date = _find_source_file(entry, today)
            date_key = source_date or today
            existing_deepdive = DAILY_DIR / "deepdive" / date_key / "deepdive.md"
            if existing_deepdive.exists():
                existing_content = existing_deepdive.read_text(encoding="utf-8")
                existing_titles = re.findall(r'^## (.+)$', existing_content, re.MULTILINE)
                if any(title.strip() == t.strip() for t in existing_titles):
                    continue
            base_dir = DAILY_DIR / "deepdive" / date_key
            downloaded_images = []
            if file_path and file_path.exists():
                content = read_file(file_path)
                all_imgs = extract_images(content)
                if all_imgs:
                    image_dir = base_dir / "images"
                    url_imgs = [(a, u, c) for a, u, c in all_imgs if u.startswith("http")]
                    local_imgs = [(a, u, c) for a, u, c in all_imgs if not u.startswith("http")]
                    if url_imgs:
                        dl = download_images(url_imgs, image_dir, safe_title)
                        downloaded_images.extend(dl)
                    if local_imgs:
                        sources_img_dir = file_path.parent / "images"
                        if sources_img_dir.exists():
                            cl = copy_local_images(local_imgs, sources_img_dir, image_dir, safe_title)
                            downloaded_images.extend(cl)
            if file_path and file_path.exists():
                prompt = build_deepdive_prompt(file_path, title, entry['brief'],
                                               prefix=safe_title, downloaded_images=downloaded_images,
                                               source_url=entry.get('source_url', ''),
                                               entry_lines=entry.get('entry_lines', ''))
            else:
                detailed_report = re.search(r'\*\*详细报告\*\*：(.+?)(?=\n\n|\n###|$)', entry['entry_lines'], re.DOTALL)
                prompt = build_deepdive_from_summary_prompt(title, entry['brief'], 
                    detailed_report.group(1).strip() if detailed_report else '',
                    source_url=entry.get('source_url', ''))
            _phase1_tasks.append({
                "id": f"deepdive_{safe_title}",
                "prompt": prompt,
                "max_tokens": 8192,
                "metadata": {"title": title, "date_key": date_key, "safe_title": safe_title},
            })
        if _phase1_tasks:
            prepare_tasks(_phase1_tasks)
        return
        for entry in entries:
            title = entry['title']

            # Find source file
            file_path, source_date = _find_source_file(entry, today)
            if not file_path:
                print(f"  Source not found, will generate from brief only")
            
            safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
            date_key = source_date or today
            base_dir = DAILY_DIR / "deepdive" / date_key

            downloaded_images = []
            image_dir = None
            if file_path and file_path.exists():
                content = read_file(file_path)
                all_imgs = extract_images(content)
                if all_imgs:
                    image_dir = base_dir / "images"
                    url_imgs = [(a, u, c) for a, u, c in all_imgs if u.startswith("http")]
                    local_imgs = [(a, u, c) for a, u, c in all_imgs if not u.startswith("http")]
                    if url_imgs:
                        dl = download_images(url_imgs, image_dir, safe_title)
                        downloaded_images.extend(dl)
                    if local_imgs:
                        sources_img_dir = file_path.parent / "images"
                        if sources_img_dir.exists():
                            cl = copy_local_images(local_imgs, sources_img_dir, image_dir, safe_title)
                            downloaded_images.extend(cl)
                    if not downloaded_images:
                        shutil.rmtree(image_dir, ignore_errors=True)
                        image_dir = None

            if file_path and file_path.exists():
                deep_report = generate_deepdive(
                    file_path, title, entry['brief'],
                    prefix=safe_title, downloaded_images=downloaded_images,
                )

            else:
                detailed_report = ''
                detailed_match = re.search(r'\*\*详细报告\*\*：(.+?)(?=\n\n|\n###|$)', entry['entry_lines'], re.DOTALL)
                if detailed_match:
                    detailed_report = detailed_match.group(1).strip()
                deep_report = generate_deepdive_from_summary(title, entry['brief'], detailed_report,
                                                              source_url=entry.get('source_url', ''))

            by_date[date_key].append((safe_title, deep_report, image_dir, title))

    # ── Write individual per-paper files + combined deepdive.md ──
    for date_key, date_results in by_date.items():
        date_dir = DAILY_DIR / "deepdive" / date_key
        date_dir.mkdir(parents=True, exist_ok=True)
        images_dir = date_dir / "images"
        combined_sections = []

        for safe_title, report, img_dir, title in date_results:
            slug = safe_title.lower().replace('__', '-').replace('_', '-')
            out_path = date_dir / f"{slug}.md"
            if report and not report.startswith("⚠️"):
                content = f"""# {title}

{report}

---
- [ ] 合入 wiki
"""
            else:
                content = f"""# {title}

⚠️ 深度阅读报告生成失败

---
- [ ] 合入 wiki
"""
            out_path.write_text(content, encoding="utf-8")
            combined_sections.append(f"## {title}\n\n[→ 阅读全文]({slug}.md)\n- [ ] 合入 wiki")

        # Also write combined deepdive.md as an index
        combined_path = date_dir / "deepdive.md"
        combined = f"# 深度阅读报告  {date_key}\n\n" + "\n\n---\n\n".join(combined_sections)
        combined_path.write_text(combined, encoding="utf-8")

        # Cleanup unused images
        if images_dir.exists():
            cleanup_deepdive_images(combined, images_dir)
            remaining = [f.name for f in images_dir.iterdir()] if images_dir.exists() else []
            if not remaining:
                shutil.rmtree(images_dir, ignore_errors=True)

    # Clean up .tmp refetch cache
    for date_key in list(by_date) + [today]:
        tmp_dir = DAILY_DIR / "deepdive" / date_key / ".tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # Summary
    total = sum(len(v) for v in by_date.values())
    for date_key, date_results in by_date.items():
        for _, _, _, title in date_results:
            print(f"  + {title}")
    print()

    # ── After phase2: update brief.md checkboxes + auto-archive ──
    if "--phase2" in sys.argv:
        import sys as _sys
        _sys.path.insert(0, str(REPO_ROOT / "tools"))
        from brief import mark_entry_done, run_archive

        brief_content = read_file(BRIEF_FILE)
        for date_key, date_results in by_date.items():
            for _, _, _, title in date_results:
                brief_content = mark_entry_done(brief_content, title, '深度阅读')
        write_file(BRIEF_FILE, brief_content)

        # Archive if any date group is fully resolved
        archived = run_archive()
        if archived:
            print(f"  ✅ 已归档: {', '.join(archived)}")


def run_direct_read(paper_input: str):
    """Direct read mode: fetch paper from arxiv/PDF/web URL, generate deep-dive report."""
    today = date.today().isoformat()
    base_dir = DAILY_DIR / "deepdive" / today
    base_dir.mkdir(parents=True, exist_ok=True)

    # Detect input type
    arxiv_id = extract_arxiv_id(paper_input)
    is_pdf = paper_input.lower().endswith('.pdf')
    is_url = paper_input.startswith('http')

    if arxiv_id:
        tmp_dir = base_dir / "deepdive" / ".tmp"
        file_path = _refetch_arxiv(arxiv_id, tmp_dir)
        source_url = f"https://arxiv.org/abs/{arxiv_id}"
    elif is_pdf:
        pdf_path = Path(paper_input).resolve()
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return
        # Convert PDF to markdown using pdf2md
        try:
            import subprocess
            tmp_md = base_dir / "deepdive" / ".tmp" / f"{pdf_path.stem}.md"
            tmp_md.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "tools" / "pdf2md.py"),
                 str(pdf_path), "-o", str(tmp_md)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                print(f"❌ pdf2md failed: {result.stderr}")
                return
            file_path = tmp_md
        except Exception as e:
            print(f"❌ PDF conversion failed: {e}")
            return
        source_url = str(pdf_path)
    elif is_url:
        tmp_dir = base_dir / "deepdive" / ".tmp"
        file_path = _refetch_web(paper_input, tmp_dir)
        source_url = paper_input
    else:
        print(f"❌ Unrecognized input: {paper_input}")
        print("   Supported: arxiv URL, PDF path, or web URL")
        return

    if not file_path or not file_path.exists():
        print(f"❌ Failed to fetch/convert content")
        return

    content = read_file(file_path)
    title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else file_path.stem


    # Extract and download images
    all_imgs = extract_images(content)
    image_dir = None
    downloaded_images = []
    if all_imgs:
        safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
        image_dir = base_dir / "images"
        url_imgs = [(a, u, c) for a, u, c in all_imgs if u.startswith("http")]
        local_imgs = [(a, u, c) for a, u, c in all_imgs if not u.startswith("http")]
        if url_imgs:
            dl = download_images(url_imgs, image_dir, safe_title)
            downloaded_images.extend(dl)
        if local_imgs:
            sources_img_dir = file_path.parent / "images"
            if sources_img_dir.exists():
                cl = copy_local_images(local_imgs, sources_img_dir, image_dir, safe_title)
                downloaded_images.extend(cl)

    # Generate report
    deep_report = generate_deepdive(
        file_path, title, "",
        prefix=''.join(c if c.isalnum() or c in '-_' else '_' for c in title),
        downloaded_images=downloaded_images,
        source_url=source_url,
    )

    # Save report — write to deepdive.md (same as pipeline deep-read)
    out_path = base_dir / "deepdive.md"
    existing = ""
    if out_path.exists():
        existing = read_file(out_path)

    section = f"## {title}\n\n- 来源: {source_url}\n\n{deep_report}\n\n- [ ] 合入 wiki"
    if existing.strip():
        combined = existing.rstrip() + "\n\n---\n\n" + section + "\n"
    else:
        combined = section + "\n"

    write_file(out_path, combined)

    # Cleanup
    if image_dir and image_dir.exists():
        cleanup_deepdive_images(combined, image_dir)

    tmp_dir = base_dir / "deepdive" / ".tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate deep-dive reading reports")
    parser.add_argument("--date", type=str, help="Process entries for specific date (YYYY-MM-DD)")
    parser.add_argument("--file", type=str, help="Process specific file")
    parser.add_argument("--paper", type=str, help="Direct read: arxiv URL, PDF path, or web URL")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--phase1", action="store_true", help="Write prompts to files for subagent processing")
    parser.add_argument("--phase2", action="store_true", help="Read results from subagent processing")
    args = parser.parse_args()

    if args.paper:
        run_direct_read(args.paper)
    else:
        run_deep_read(
            date_str=args.date,
            file_name=args.file,
            json_output=args.json,
        )
