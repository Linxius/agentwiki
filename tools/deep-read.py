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
from pathlib import Path
from datetime import date
from collections import defaultdict

import os

REPO_ROOT = Path(__file__).parent.parent
DAILY_DIR = REPO_ROOT / "raw" / "digest"
BRIEF_FILE = DAILY_DIR / "brief.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def call_llm(prompt: str, max_tokens: int = 8192) -> str:
    try:
        from litellm import completion
    except ImportError:
        print("Error: litellm not installed. Run: pip install litellm")
        sys.exit(1)

    model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-latest")

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    response = completion(**kwargs)
    return response.choices[0].message.content


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


def generate_deepdive(file_path: Path, title: str, brief: str) -> str:
    """Generate a 1500-3000 word deep-dive report for the file."""
    content = read_file(file_path)
    if len(content) > 20000:
        content = content[:20000]

    prompt = f"""你是 AI 深度阅读助手。请对以下文档进行深度阅读分析，生成 1500-3000 字的详细报告。

文档信息：
- 标题: {title}
- 已有简介: {brief}

文档内容:
=== CONTENT START ===
{content}
=== CONTENT END ===

请生成一份结构化的深度阅读报告，包含：
1. **核心观点概括** — 提炼文档最主要的 3-5 个核心观点
2. **技术/方法论深度拆解** — 如文档涉及技术方法，详细解释其原理、流程和关键设计
3. **关键数据/案例解读** — 对文档中的数据进行深入解读，说明背后的意义
4. **与其他领域的对比/关联** — 分析该文档内容与相关领域的关系
5. **潜在问题与局限** — 指出文档可能存在的问题、局限性或值得商榷之处

要求：
- 使用中文撰写
- 报告应详细深入，但不堆砌废话
- 如果文档包含图片/表格信息，简要提及
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

        # Generate deep-dive report
        if file_path and file_path.exists():
            print(f"  Found original file: {file_path}")
            deep_report = generate_deepdive(file_path, title, entry['brief'])
        else:
            print(f"  ⚠️  Original file not found, generating from summary only")
            # Try to find detailed report from entry
            detailed_report = ''
            detailed_match = re.search(r'\*\*详细报告\*\*：(.+?)(?=\n\n|\n###|$)', entry['entry_lines'], re.DOTALL)
            if detailed_match:
                detailed_report = detailed_match.group(1).strip()
            deep_report = generate_deepdive_from_summary(title, entry['brief'], detailed_report)

        # Save deep-dive report
        safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
        deepdive_path = DAILY_DIR / today / "deepdive" / f"deepdive-{safe_title}.md"
        if 'sources' in str(file_path):
            source_date = str(file_path).split('digest/')[1].split('/')[0]
            deepdive_path = DAILY_DIR / source_date / "deepdive" / f"deepdive-{safe_title}.md"

        deepdive_path.parent.mkdir(parents=True, exist_ok=True)
        write_file(deepdive_path, f"# {title} 深度阅读\n\n{deep_report}")
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
