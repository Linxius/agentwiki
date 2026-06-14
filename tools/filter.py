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
    6. Move files to raw/digest/YYYY-MM-DD/sources/
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
from pathlib import Path
from datetime import date
from collections import defaultdict

import os

REPO_ROOT = Path(__file__).parent.parent
INBOX_DIR = REPO_ROOT / "raw" / "inbox"
DAILY_DIR = REPO_ROOT / "raw" / "digest"
BRIEF_DIR = DAILY_DIR / "brief"
BRIEF_FILE = DAILY_DIR / "brief.md"
CATEGORIES = [
    "articles", "datasets", "docs", "books",
    "papers", "projects", "talks",
]
INTERESTS_FILE = REPO_ROOT / "wiki" / "interests.md"
LOG_FILE = REPO_ROOT / "wiki" / "log.md"
SCHEMA_FILE = REPO_ROOT / "AGENTS.md"


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


def parse_interests(content: str) -> list[dict]:
    """Parse interests from wiki/interests.md content."""
    interests = []
    current_category = None

    for line in content.split("\n"):
        line = line.strip()

        cat_match = re.match(r'^## (.+)$', line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue

        if line.startswith("- name:"):
            interest = {"name": line.split(":", 1)[1].strip(), "category": current_category or "未分类"}
            interests.append(interest)
        elif line.startswith("weight:") and interests:
            interests[-1]["weight"] = float(line.split(":", 1)[1].strip())
        elif line.startswith("keywords:") and interests:
            kw_str = line.split(":", 1)[1].strip()
            kw_match = re.match(r'\[(.+)\]', kw_str)
            if kw_match:
                interests[-1]["keywords"] = [k.strip() for k in kw_match.group(1).split(",")]
        elif line.startswith("description:") and interests:
            interests[-1]["description"] = line.split(":", 1)[1].strip()

    for interest in interests:
        interest.setdefault("weight", 0.5)
        interest.setdefault("keywords", [])
        interest.setdefault("description", "")

    return interests


def get_file_preview(file_path: Path) -> str:
    """Get first 4000 chars of file for LLM analysis."""
    content = read_file(file_path)
    if len(content) <= 4000:
        return content
    return content[:4000]


def extract_source_url(file_path: Path) -> str:
    """Try to extract URL from file metadata, filename, or content."""
    # If filename looks like a URL or has URL info
    name = file_path.stem
    for word in name.split('-'):
        if word.startswith('http') or 'arxiv' in word.lower() or '.org' in word:
            return f"https://{word}"

    # Try to find URL in first 100 lines
    content = read_file(file_path)
    lines = content.split('\n')
    for line in lines[:100]:
        line = line.strip()
        if line.startswith('url: ') or line.startswith('URL: '):
            return line.split(': ', 1)[1].strip()
        if line.startswith('> url: ') or line.startswith('source_url: '):
            url = line.split(':', 1)[1].strip()
            if url:
                return url
        if line.startswith('http') and '://' in line:
            return line.split()[0]

    # If file is from wiki already, return its path
    return file_path.as_posix()  # Use posix path for cross-platform


def analyze_file(file_path: Path, interests: list[dict]) -> dict:
    """Use LLM to analyze file and generate summary + match against interests."""
    if not interests:
        print("  Warning: No interests defined. Generating summary only.")

    schema = read_file(SCHEMA_FILE)
    preview = get_file_preview(file_path)
    source_url = extract_source_url(file_path)

    interests_desc = ""
    for interest in interests:
        kw_str = ", ".join(interest.get("keywords", []))
        interests_desc += f"- {interest['name']}:\n  - 权重: {interest.get('weight', 0.5)}\n  - 关键词: [{kw_str}]\n  - 描述: {interest.get('description', '')}\n"

    # Detect if file might contain multiple items (arxiv list, newsletter, etc.)
    is_multientry = any(kw in preview.lower() for kw in [
        "arxiv", "paper", "list", "summary", "newsletter", "digest",
        "bulletin", "weekly", "daily", "top", "most", "recent",
    ])

    if is_multientry:
        # Multi-entry mode: expect array of entries
        entries_prompt = """IMPORTANT: This document may contain MULTIPLE independent items (papers, news, etc.).
You MUST extract EACH distinct item as a separate entry.

Return a JSON ARRAY of objects (not a single object):
[
  {{
    "item_id": 1,
    "title": "title of item 1",
    "source_url": "url of item 1 if available, else null",
    "match_level": "interested | possibly_interested | not_interested",
    "matched_interests": ["interests"],
    "reason": "why it matches (1-2 sentences)",
    "brief": "3-5 sentence summary of item 1",
    "detailed_report": "500-800 word detailed report about item 1 in Chinese"
  }},
  {{
    "item_id": 2,
    "title": "title of item 2",
    "source_url": "url of item 2 if available, else null",
    "match_level": "interested | possibly_interested | not_interested",
    "matched_interests": ["interests"],
    "reason": "why it matches (1-2 sentences)",
    "brief": "3-5 sentence summary of item 2",
    "detailed_report": "500-800 word detailed report about item 2 in Chinese"
  }}
]

For each item:
- Extract its title if it has one
- Find any associated URL (arxiv, github, etc.)
- Assess match against user interests independently
- Write a focused 500-800 word report about THIS specific item only
"""
    else:
        # Single-entry mode
        entries_prompt = """Return a JSON ARRAY with exactly ONE object (one item):
[
  {{
    "item_id": 1,
    "title": "document title",
    "source_url": "url if available, else null",
    "match_level": "interested | possibly_interested | not_interested",
    "matched_interests": ["interests"],
    "reason": "brief explanation (1-2 sentences)",
    "brief": "3-5 sentence summary",
    "detailed_report": "500-800 word detailed report in Chinese covering background, methods, key data/insights, and relevance to interests"
  }}
]"""

    prompt = f"""You are an AI assistant analyzing research materials. Analyze the following document and extract all independent items with their interest matches.

Schema and conventions:
{schema}

Current interests:
{interests_desc if interests_desc else "No specific interests defined."}

Document to analyze (file: {file_path.name}):
=== DOCUMENT START ===
{preview}
=== DOCUMENT END ===

{entries_prompt}

CRITICAL: Return ONLY the JSON array. No markdown fences, no prose.
"""

    try:
        raw = call_llm(prompt, max_tokens=8192)
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        data = json.loads(raw)
    except Exception as e:
        print(f"  ⚠️  LLM analysis failed for {file_path.name}: {e}")
        # Fallback with basic info
        data = [{
            "item_id": 1,
            "match_level": "not_interested",
            "matched_interests": [],
            "reason": "LLM analysis failed",
            "brief": f"A document titled '{file_path.name}'.",
            "detailed_report": f"No detailed report available. File: {file_path.name}。\n\n来源：{source_url}",
            "title": file_path.stem,
            "source_url": source_url,
            "suggested_category": "papers",
        }]

    if not isinstance(data, list):
        data = [data]

    results = []
    for entry in data:
        results.append({
            "file": file_path,
            "item_id": entry.get("item_id", 1),
            "match_level": entry.get("match_level", "not_interested"),
            "matched_interests": entry.get("matched_interests", []),
            "reason": entry.get("reason", ""),
            "suggested_category": entry.get("suggested_category", "papers"),
            "title": entry.get("title", file_path.stem),
            "brief": entry.get("brief", ""),
            "detailed_report": entry.get("detailed_report", ""),
            "source_url": entry.get("source_url") or source_url,
        })

    return results


def generate_brief_entries(results: list[dict]) -> str:
    """Generate the brief.md content from analysis results."""
    today = date.today().isoformat()
    lines = [f"# 资讯简报  {today}\n"]
    lines.append("")

    # Group by match level
    groups = {
        "interested": ("## [感兴趣]", "## [感兴趣]"),
        "possibly_interested": ("## [可能感兴趣]", "## [可能感兴趣 — 部分匹配/主题相关]"),
        "not_interested": ("## [不感兴趣]", "## [不感兴趣]"),
    }

    for level in ["interested", "possibly_interested", "not_interested"]:
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
                lines.append(f"- 匹配: {', '.join(item['matched_interests']) if item['matched_interests'] else '无'}")
                lines.append(f"- 理由: {item['reason']}")
                lines.append(f"- [ ] 深度阅读")
                lines.append(f"- [ ] 合入 wiki")
                lines.append("")
                lines.append(f"**简介**：{item['brief']}")
                lines.append("")
                lines.append(f"**详细报告**：")
                lines.append(item['detailed_report'])
                lines.append("")

    return "\n".join(lines)


def archive_current_brief():
    """Archive current brief.md to digest/brief/YYYY-MM-DD.md if it exists."""
    today = date.today().isoformat()
    if BRIEF_FILE.exists():
        archive_path = BRIEF_DIR / f"{today}.md"
        if archive_path.exists():
            # Append to existing archive
            existing = read_file(BRIEF_FILE)
            archive_content = read_file(archive_path)
            archive_content += "\n\n---\n\n" + existing + f"\n\n**归档于: {today}**"
            write_file(archive_path, archive_content)
        else:
            shutil.copy2(str(BRIEF_FILE), str(archive_path))


def generate_new_brief():
    """After archiving, create a minimal brief.md placeholder for today."""
    today = date.today().isoformat()
    content = f"""# 资讯简报

---

## 今日暂无待处理资讯

---

## 操作指引

- 勾选「深度阅读」后，告诉 agent 生成详细解读
- 勾选「合入 wiki」后，告诉 agent 执行合入

## 状态说明

- **待处理**：已筛选，待确认
- **已深度阅读**：已生成深度阅读报告
- **已合入**：已合并到 wiki
- **已跳过**：用户选择不处理

"""
    write_file(BRIEF_FILE, content)


def inject_source_url(file_path: Path, source_url: str):
    """Inject source_url into file's YAML frontmatter as url: field.

    If file already has YAML frontmatter, add/update url: field.
    If no frontmatter, prepend one with url: field.
    Skips if source_url is empty or is just the file path itself.
    """
    if not source_url or source_url == file_path.as_posix():
        return

    content = read_file(file_path)
    fmatch = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

    if fmatch:
        frontmatter = fmatch.group(1)
        rest = content[fmatch.end():]

        if re.search(r'^url:\s*', frontmatter, re.MULTILINE):
            frontmatter = re.sub(
                r'^url:\s*.*$',
                f'url: {source_url}',
                frontmatter,
                flags=re.MULTILINE,
            )
        else:
            first_nl = frontmatter.index('\n') + 1 if '\n' in frontmatter else len(frontmatter)
            frontmatter = frontmatter[:first_nl] + f'url: {source_url}\n' + frontmatter[first_nl:]

        new_content = f'---\n{frontmatter}\n---\n{rest}'
    else:
        new_content = f'---\nurl: {source_url}\n---\n{content}'

    file_path.write_text(new_content, encoding='utf-8')


def move_file_to_daily(file_path: Path, date_str: str):
    """Move file to digest/YYYY-MM-DD/sources/."""
    dest_dir = DAILY_DIR / date_str / "sources"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file_path.name

    if not dest_path.exists():
        shutil.move(str(file_path), str(dest_path))
    return dest_path


def clear_inbox():
    """Clear inbox/ directory."""
    if not INBOX_DIR.exists():
        return
    inbox_files = list(INBOX_DIR.iterdir())
    if not inbox_files:
        print("  inbox/ 已为空。")
        return

    count = len(inbox_files)
    for f in inbox_files:
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)
    print(f"  ✅ 已清空 inbox/ ({count} 个文件)")


def append_log(entry: str):
    existing = read_file(LOG_FILE)
    write_file(LOG_FILE, entry.strip() + "\n\n" + existing)


def run_filter(dry_run: bool = False, json_output: bool = False):
    """Main filter flow."""
    # Ensure directories exist
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    files = [f for f in INBOX_DIR.iterdir() if f.is_file() and f.suffix.lower() in {".md", ".pdf", ".txt", ".html", ".docx", ".pptx", ".xlsx"}]

    if not files:
        print("inbox/ 中没有可筛选的文件。")
        return

    print(f"找到 {len(files)} 个文件待筛选。\n")

    # Read interests
    interests = []
    interests_content = read_file(INTERESTS_FILE)
    if interests_content:
        interests = parse_interests(interests_content)
        print(f"读取到 {len(interests)} 个兴趣点。\n")
    else:
        print("  提示：wiki/interests.md 为空，仅生成摘要不匹配兴趣。\n")

    # Analyze files
    results = []
    for file_path in files:
        print(f"  分析: {file_path.name}")
        file_results = analyze_file(file_path, interests)
        for r in file_results:
            results.append(r)
            print(f"    → {r['file'].name}: {r['match_level']} ({r['suggested_category']})")

    # Inject source URL into each file's frontmatter before moving
    injected = set()
    for r in results:
        fp = r['file']
        if fp not in injected and r.get('source_url'):
            inject_source_url(fp, r['source_url'])
            injected.add(fp)

    # Sort results: interested > possibly_interested > not_interested
    priority = {"interested": 0, "possibly_interested": 1, "not_interested": 2}
    results.sort(key=lambda x: priority.get(x["match_level"], 3))

    # Generate brief.md
    brief_content = generate_brief_entries(results)

    if not dry_run:
        # Archive current brief if it exists
        if BRIEF_FILE.exists():
            print("  正在归档旧 brief...")
            archive_current_brief()
            generate_new_brief()

        # Write today's brief
        write_file(BRIEF_FILE, brief_content)

        # Move files to digest/YYYY-MM-DD/sources/
        today = date.today().isoformat()
        for item in results:
            print(f"  移动: {item['file'].name} → {today}/sources/")
            source_dest = move_file_to_daily(item["file"], today)
            print(f"    ✅ {source_dest}")

        # clear inbox
        clear_inbox()

    # Log
    log_entry = f"## [{date.today().isoformat()}] filter | {len(results)} files processed"
    append_log(log_entry)

    if json_output:
        json_results = []
        for r in results:
            json_results.append({
                "file": str(r["file"].relative_to(REPO_ROOT)),
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

    print(f"\n✅ 筛选完成！报告已保存到: {BRIEF_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and classify files in raw/inbox/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without moving files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    run_filter(dry_run=args.dry_run, json_output=args.json)
