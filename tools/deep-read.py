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
    3. Save report to raw/digest/YYYY-MM-DD/deepdive-<filename>.md
    4. Update brief.md status

Output:
    - raw/digest/YYYY-MM-DD/deepdive-*.md  — deep-dive reading report
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


def download_images(images, dest_dir):
    """Download images to dest_dir/{fig1.ext, ...}. Returns list of (url, filename, alt)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for idx, (alt, url, ctx) in enumerate(images):
        ext = Path(url.split('?')[0]).suffix.lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
            ext = '.png'
        filename = f"fig{idx + 1}{ext}"
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


def build_image_prompt_section(downloaded, safe_title):
    """Build image info block for LLM prompt. Empty string if no images."""
    if not downloaded:
        return ""
    parts = ["\n---\n源文档中包含以下图片："]
    for url, filename, alt in downloaded:
        caption = alt if alt else '(无标题)'
        parts.append(f"- `{filename}` — {caption} ({url})")
    parts += [
        "",
        "请判断哪些是核心**算法图、架构图、流程图**等结构性图片。",
        f"在报告中用 `![图片标题](deepdive-{safe_title}/{filename})` 引用它们。",
        "忽略非结构性的装饰图（如结果对比图、示例截图、数据集样本等）。",
    ]
    return "\n".join(parts)


def copy_local_images(images, source_dir, dest_dir):
    """Copy local images from source_dir (sources/images/) to dest_dir.
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
        filename = f"fig{idx + 1}{ext}"
        src = Path(source_dir) / url
        if src.exists():
            if src.stat().st_size > MAX_IMAGE_SIZE:
                continue
            dest = dest_dir / filename
            shutil.copy2(str(src), str(dest))
            copied.append((url, filename, alt))
    return copied


def cleanup_images(report_content, image_dir, safe_title):
    """Remove unreferenced images from image_dir."""
    if not image_dir or not image_dir.exists():
        return
    ref_prefix = f"deepdive-{safe_title}/"
    referenced = set()
    for m in re.finditer(r'\]\(' + re.escape(ref_prefix) + r'([^)]+)\)', report_content):
        referenced.add(m.group(1))
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
                # Extract source URL
                source_url = ''
                url_match = re.search(r'- 来源:\s*(.+)', entry_text)
                if url_match:
                    source_url = url_match.group(1).strip()

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
                    'brief': brief,
                    'entry_lines': entry_text,
                    'deepdive_existed': deepdive_existed,
                })

            i = next_i
        else:
            i += 1

    return entries


def generate_deepdive(file_path: Path, title: str, brief: str,
                      safe_title: str = "", downloaded_images: list = None) -> str:
    """Generate a 1500-3000 word deep-dive report for the file."""
    content = read_file(file_path)
    if len(content) > 20000:
        content = content[:20000]

    img_section = ""
    if downloaded_images:
        img_section = build_image_prompt_section(downloaded_images, safe_title)

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
- 对于重要图片（算法图、架构图、流程图），用 ![图片标题](deepdive-{safe_title}/{filename}) 在报告中引用
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
                    brief = ''
                    brief_match = re.search(r'\*\*简介\*\*：(.+?)(?=\*\*详细报告\*\*|\n\n|$)', entry_text, re.DOTALL)
                    if brief_match:
                        brief = brief_match.group(1).strip()
                    entries.append({
                        'title': file_name,
                        'source_url': '',
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

    # Process each entry
    today = date.today().isoformat()
    results = []

    for entry in entries:
        title = entry['title']
        print(f"Processing: {title}")

        # Try to find the original file
        file_path = None
        for root_dir in [DAILY_DIR / today / "sources"]:
            if root_dir.exists():
                for f in root_dir.iterdir():
                    if title in f.name or f.name.startswith(title.split('.')[0]):
                        file_path = f
                        break
                if file_path:
                    break

        # Prepare safe_title and paths
        safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
        deepdive_path = DAILY_DIR / today / "deepdive" / f"deepdive-{safe_title}.md"
        if file_path and 'sources' in str(file_path):
            source_date = str(file_path).split('digest/')[1].split('/')[0]
            deepdive_path = DAILY_DIR / source_date / "deepdive" / f"deepdive-{safe_title}.md"

        # Extract and download/copy images from source
        downloaded_images = []
        image_dir = None
        if file_path and file_path.exists():
            content = read_file(file_path)
            all_imgs = extract_images(content)
            if all_imgs:
                image_dir = deepdive_path.parent / f"deepdive-{safe_title}"
                print(f"  Found {len(all_imgs)} images in source")
                url_imgs = [(a, u, c) for a, u, c in all_imgs if u.startswith("http")]
                local_imgs = [(a, u, c) for a, u, c in all_imgs if not u.startswith("http")]
                if url_imgs:
                    dl = download_images(url_imgs, image_dir)
                    downloaded_images.extend(dl)
                if local_imgs:
                    sources_img_dir = file_path.parent / "images"
                    if sources_img_dir.exists():
                        cl = copy_local_images(local_imgs, sources_img_dir, image_dir)
                        downloaded_images.extend(cl)
                if downloaded_images:
                    print(f"    Acquired {len(downloaded_images)} images for LLM selection")
                if not downloaded_images:
                    shutil.rmtree(image_dir, ignore_errors=True)
                    image_dir = None

        # Generate deep-dive report
        if file_path and file_path.exists():
            print(f"  Found original file: {file_path}")
            deep_report = generate_deepdive(
                file_path, title, entry['brief'],
                safe_title=safe_title, downloaded_images=downloaded_images,
            )
        else:
            print(f"  ⚠️  Original file not found, generating from summary only")
            detailed_report = ''
            detailed_match = re.search(r'\*\*详细报告\*\*：(.+?)(?=\n\n|\n###|$)', entry['entry_lines'], re.DOTALL)
            if detailed_match:
                detailed_report = detailed_match.group(1).strip()
            deep_report = generate_deepdive_from_summary(title, entry['brief'], detailed_report)

        # Save deep-dive report and clean up unreferenced images
        deepdive_path.parent.mkdir(parents=True, exist_ok=True)
        write_file(deepdive_path, f"# {title} 深度阅读\n\n{deep_report}")
        if image_dir and image_dir.exists():
            cleanup_images(deep_report, image_dir, safe_title)
            remaining = [f.name for f in image_dir.iterdir()] if image_dir.exists() else []
            if remaining:
                print(f"    Images kept: {len(remaining)} in {image_dir.name}/")
            else:
                shutil.rmtree(image_dir, ignore_errors=True)
        print(f"  ✅ Saved: {deepdive_path.relative_to(REPO_ROOT)}")
        results.append({
            'title': title,
            'path': str(deepdive_path.relative_to(REPO_ROOT)),
            'success': True,
        })

    # Update brief.md marker
    # New simple flag to indicate deep-read completed
    updated_brief = brief_content
    if not json_output:
        write_file(BRIEF_FILE, updated_brief)

    # Summary
    print(f"\n{'='*50}")
    print(f"✅ Deep-read generation complete!")
    for r in results:
        print(f"  + {r['title']} → {r['path']}")
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
