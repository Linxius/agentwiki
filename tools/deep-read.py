#!/usr/bin/env python3
"""
Generate deep-dive reading reports for selected files.

Usage:
    python tools/deep-read.py              # process all checked in brief.md
    python tools/deep-read.py --date YYYY-MM-DD  # process specific date
    python tools/deep-read.py --file filename.md  # process single file

Flow:
    1. Read raw/digest/brief.md to find files marked "[x] 深度阅读"
    2. For each checked file, call LLM to generate 1500-3000 word deep-dive report
    3. Accumulate reports by date, save as raw/digest/YYYY-MM-DD/deepdive.md
    4. Images go to deepdive/ directory, prefixed by entry slug

Output:
    - raw/digest/YYYY-MM-DD/deepdive.md    — combined deep-dive report (一天一份)
    - raw/digest/YYYY-MM-DD/deepdive/      — images (文件名: {slug}-figN.ext)
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

from _utils import read_file, write_file, call_llm

REPO_ROOT = Path(__file__).parent.parent
DAILY_DIR = REPO_ROOT / "raw" / "digest"
BRIEF_FILE = DAILY_DIR / "brief.md"
MAX_IMAGE_SIZE = 2 * 1024 * 1024

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
        return out_file

    try:
        from arxiv2md import ingest_paper_sync
        result = ingest_paper_sync(arxiv_id)
        out_file.write_text(result.content, encoding="utf-8")
        return out_file
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
            return out_file
    except Exception:
        pass

    out_file.write_text(f"# arXiv: {arxiv_id}\n\n[Unable to re-fetch content]\n\nOriginal: https://arxiv.org/abs/{arxiv_id}\n", encoding="utf-8")
    return out_file


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
    first = f"deepdive/{downloaded[0][1]}"  # first image full relative path
    parts = ["\n---\n源文档中包含以下图片："]
    for url, filename, alt in downloaded:
        caption = alt if alt else '(无标题)'
        img_path = f"deepdive/{filename}"
        parts.append(f"- `{img_path}` — {caption} ({url})")
    parts += [
        "",
        "请判断哪些是核心**算法图、架构图、流程图**等结构性图片。",
        f"在报告中用 `![图片标题]({first})` 等路径引用它们（相对于 deepdive.md）。",
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


def find_checked_entries(brief_content: str, date_str: str = None) -> list[dict]:
    """Parse brief.md to find entries marked "[x] 深度阅读"."""
    entries = []
    lines = brief_content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if it's a section header for a file
        if line.startswith('### ') and not line.startswith('### ['):
            file_title = line[4:].strip()

            # Check if it's within the specified date
            if date_str:
                # Look back for date header
                found_date = False
                for j in range(max(0, i-10), i):
                    if date_str in lines[j]:
                        found_date = True
                        break
                if not found_date:
                    i += 1
                    continue

            # Collect the entry's lines
            entry_lines = []
            next_i = i + 1
            while next_i < len(lines):
                if lines[next_i].startswith('### ') and not lines[next_i].startswith('### ['):
                    break
                entry_lines.append(lines[next_i])
                next_i += 1

            entry_text = '\n'.join(entry_lines)

            # Check if "[x] 深度阅读" is present
            if re.search(r'\[x\]\s*深度阅读|\[X\]\s*深度阅读', entry_text):
                # Extract source URL and source file path
                source_url = ''
                url_match = re.search(r'- 来源:\s*(.+)', entry_text)
                if url_match:
                    source_url = url_match.group(1).strip()

                source_path = ''
                path_match = re.search(r'- 源文件:\s*(.+)', entry_text)
                if path_match:
                    source_path = path_match.group(1).strip()

                # Extract brief and detail report if available
                brief = ''
                brief_match = re.search(r'\*\*简介\*\*：(.+?)(?=\*\*详细报告\*\*|\n\n|$)', entry_text, re.DOTALL)
                if brief_match:
                    brief = brief_match.group(1).strip()

                # Check if deepdive already exists
                deepdive_existed = 'deepdive' in entry_text.lower()

                entries.append({
                    'title': file_title,
                    'source_url': source_url,
                    'source_path': source_path,
                    'brief': brief,
                    'entry_lines': entry_text,
                    'deepdive_existed': deepdive_existed,
                })

            i = next_i
        else:
            i += 1

    return entries


def generate_deepdive(file_path: Path, title: str, brief: str,
                      prefix: str = "", downloaded_images: list = None) -> str:
    """Generate a 1500-3000 word deep-dive report for the file."""
    content = read_file(file_path)
    if len(content) > 20000:
        content = content[:20000]

    img_section = ""
    if downloaded_images:
        img_section = build_image_prompt_section(downloaded_images, prefix)
        example_img = f"deepdive/{downloaded_images[0][1]}"
    else:
        example_img = ""

    prompt = f"""你是 AI 深度阅读助手。请对以下文档进行深度阅读分析，生成 1500-3000 字的详细报告。

文档信息：
- 标题: {title}
- 已有简介: {brief}

文档内容:
=== CONTENT START ===
{content}
=== CONTENT END ===
{img_section}

请生成一份结构化的深度阅读报告，包含：
1. **核心观点概括** — 提炼文档最主要的 3-5 个核心观点
2. **技术/方法论深度拆解** — 如文档涉及技术方法，详细解释其原理、流程和关键设计
3. **关键数据/案例解读** — 对文档中的数据进行深入解读，说明背后的意义
4. **与其他领域的对比/关联** — 分析该文档内容与相关领域的关系
5. **潜在问题与局限** — 指出文档可能存在的问题、局限性或值得商榷之处

要求：
- 使用中文撰写
- 报告应详细深入，但不堆砌废话
- 对于重要图片（算法图、架构图、流程图），用 `![图片标题]({example_img})` 等路径在报告中引用
- 不要出现 [[wikilinks]] 格式
- 不要使用 markdown code fences

直接输出报告内容，不要添加 "以下是深度阅读报告" 等开场白。"""

    try:
        raw = call_llm(prompt, max_tokens=8192)
        raw = re.sub(r"^```(?:markdown)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        return raw
    except Exception as e:
        return f"⚠️ 深度阅读生成失败：{e}"


def generate_deepdive_from_summary(title: str, brief: str, detailed_report: str) -> str:
    """Generate deep report from existing summary and detailed report."""
    # If we don't have the original file, generate from brief + detailed report
    prompt = f"""你是 AI 深度阅读助手。请基于以下文档信息，生成一份 1500-3000 字的深度阅读报告。

文档信息：
- 标题: {title}
- 已有简介: {brief}
- 已有详细报告: {detailed_report}

请在此基础上扩展一份更深入的阅读报告，包含：
1. **核心观点深度分析** — 对已有内容进行深度解读
2. **技术/方法论深度拆解** — 详细解释原理和关键设计
3. **关键数据/案例解读** — 深入解读数据背后的意义
4. **与其他领域的对比/关联** — 分析与其他领域的关系
5. **潜在问题与局限** — 指出可能的问题

要求：
- 使用中文撰写
- 内容要有深度和洞察，避免简单复述
- 不要出现 [[wikilinks]] 格式
- 直接输出报告内容
"""

    try:
        raw = call_llm(prompt, max_tokens=8192)
        raw = re.sub(r"^```(?:markdown)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
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
        if f"### {title_to_process}" in lines[max(0, i-3):i+1]:
            # We're near the target entry
            pass

        # Simple approach: find "[x] 深度阅读" and if this is a target entry, mark it differently
        if '[x] 深度阅读' in line or '[X] 深度阅读' in line:
            # Check if we're at a target entry (look back for title)
            for j in range(max(0, i-20), i):
                if lines[j].startswith(f'### {title_to_process}') or title_to_process in lines[j]:
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

    # Find checked entries
    if date_str:
        entries = find_checked_entries(brief_content, date_str)
    elif file_name:
        # Find entry with this filename
        entries = []
        lines = brief_content.split('\n')
        i = 0
        while i < len(lines):
            if f"### {file_name}" in lines[i]:
                entry_lines = []
                next_i = i + 1
                while next_i < len(lines) and not lines[next_i].startswith('### '):
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

    if not entries:
        print("No entries marked for deep-read.")
        if date_str:
            print(f"  Check brief.md for entries with [x] 深度阅读 on {date_str}")
        elif file_name:
            print(f"  Check brief.md for entry '{file_name}' with [x] 深度阅读")
        else:
            print("  Check brief.md for entries with [x] 深度阅读")
        return

    print(f"Found {len(entries)} entries marked for deep-read.\n")

    today = date.today().isoformat()

    # Accumulate results by date
    by_date = defaultdict(list)  # date_key -> [(safe_title, report, image_dir, title)]

    for entry in entries:
        title = entry['title']
        print(f"Processing: {title}")

        # ── Find source file ──
        file_path = None
        source_date = None

        # 1. source_path from brief.md
        if entry.get('source_path'):
            candidate = (REPO_ROOT / entry['source_path']).resolve()
            if candidate.exists():
                file_path = candidate

        # 2. Guess by name (legacy)
        if not file_path:
            for root_dir in [DAILY_DIR / today / "sources"]:
                if root_dir.exists():
                    for f in root_dir.iterdir():
                        if title in f.name or f.name.startswith(title.split('.')[0]):
                            file_path = f
                            break
                if file_path:
                    break

        # 3. Re-fetch from URL
        if not file_path and entry.get('source_url'):
            print(f"  Source not found, re-fetching from URL...")
            tmp_dir = DAILY_DIR / today / "deepdive" / ".tmp"
            tmp_fetched = refetch_source(entry['source_url'], tmp_dir)
            if tmp_fetched and tmp_fetched.exists():
                file_path = tmp_fetched
                print(f"    Re-fetched → {tmp_fetched.relative_to(REPO_ROOT)}")

        # ── Prepare paths ──
        safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
        if file_path:
            m = re.search(r'digest/(\d{4}-\d{2}-\d{2})/', str(file_path))
            if m:
                source_date = m.group(1)
        date_key = source_date or today
        base_dir = DAILY_DIR / date_key

        # ── Extract & download images ──
        downloaded_images = []
        image_dir = None
        if file_path and file_path.exists():
            content = read_file(file_path)
            all_imgs = extract_images(content)
            if all_imgs:
                image_dir = base_dir / "deepdive"
                print(f"  Found {len(all_imgs)} images in source")
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
                if downloaded_images:
                    print(f"    Acquired {len(downloaded_images)} images for LLM selection")
                else:
                    shutil.rmtree(image_dir, ignore_errors=True)
                    image_dir = None

        # ── Generate deep-dive report ──
        if file_path and file_path.exists():
            print(f"  Source: {file_path.relative_to(REPO_ROOT)}")
            deep_report = generate_deepdive(
                file_path, title, entry['brief'],
                prefix=safe_title, downloaded_images=downloaded_images,
            )
        else:
            print(f"  ⚠️  Source not found, generating from brief only")
            detailed_report = ''
            detailed_match = re.search(r'\*\*详细报告\*\*：(.+?)(?=\n\n|\n###|$)', entry['entry_lines'], re.DOTALL)
            if detailed_match:
                detailed_report = detailed_match.group(1).strip()
            deep_report = generate_deepdive_from_summary(title, entry['brief'], detailed_report)

        by_date[date_key].append((safe_title, deep_report, image_dir, title))
        print(f"    ✓ {title}")

    # ── Write combined deepdive.md per date ──
    for date_key, date_results in by_date.items():
        md_path = DAILY_DIR / date_key / "deepdive.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)

        sections = []
        for safe_title, report, img_dir, title in date_results:
            sections.append(f"## {title}\n\n{report}")

        combined = "\n\n---\n\n".join(sections)
        write_file(md_path, combined)
        print(f"\n  ✅ Written: {md_path.relative_to(REPO_ROOT)}")

        # One cleanup pass for all images
        img_dir = md_path.parent / "deepdive"
        if img_dir.exists():
            cleanup_deepdive_images(combined, img_dir)
            remaining = [f.name for f in img_dir.iterdir()] if img_dir.exists() else []
            if remaining:
                print(f"    Images kept: {len(remaining)} in deepdive/")
            else:
                shutil.rmtree(img_dir, ignore_errors=True)

    # ── Update brief.md marker ──
    updated_brief = brief_content
    if not json_output:
        write_file(BRIEF_FILE, updated_brief)

    # Clean up .tmp refetch cache
    for date_key in list(by_date) + [today]:
        tmp_dir = DAILY_DIR / date_key / "deepdive" / ".tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # Summary
    total = sum(len(v) for v in by_date.values())
    print(f"\n{'='*50}")
    print(f"✅ Deep-read generation complete! {total} entries in {len(by_date)} date(s).")
    for date_key, date_results in by_date.items():
        for _, _, _, title in date_results:
            print(f"  + {title}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate deep-dive reading reports")
    parser.add_argument("--date", type=str, help="Process entries for specific date (YYYY-MM-DD)")
    parser.add_argument("--file", type=str, help="Process specific file")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    run_deep_read(
        date_str=args.date,
        file_name=args.file,
        json_output=args.json,
    )
