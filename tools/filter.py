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
from concurrent.futures import ThreadPoolExecutor, as_completed

import os

from _utils import read_file, write_file, call_llm, inject_source_url

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
    """Get file preview for LLM. Papers: abstract + intro. Others: first 8000 chars."""
    content = read_file(file_path)
    if len(content) <= 8000:
        return content

    # Detect paper: has Introduction section
    has_intro = re.search(r'^##\s+(1\s+)?[Ii]ntroduction', content, re.MULTILINE)

    if not has_intro:
        return content[:8000]

    # Extract YAML frontmatter
    parts = []
    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if yaml_match:
        parts.append(yaml_match.group(0))

    # Extract Abstract section
    abs_match = re.search(
        r'(##\s+[Aa]bstract|##\s+摘要|\*\*摘要\*\*)'
        r'(.*?)(?=\n##\s+\d?\s*[A-Z]|\n##\s+[A-Z]|\Z)',
        content, re.DOTALL
    )
    if abs_match:
        parts.append(abs_match.group(0))

    # Extract Introduction (first 2000 chars)
    intro_match = re.search(r'^##\s+(1\s+)?[Ii]ntroduction\n(.*)', content, re.MULTILINE | re.DOTALL)
    if intro_match:
        intro = intro_match.group(2)[:2000]
        parts.append(f"## Introduction\n{intro}")

    result = '\n\n'.join(parts)
    return result[:8000] if result else content[:8000]


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


def analyze_file(file_path: Path, interests_desc: str) -> list[dict]:
    """Use LLM to analyze file. interests_desc is precompiled from run_filter()."""
    if not interests_desc.strip():
        print("  Warning: No interests defined. Generating summary only.")

    preview = get_file_preview(file_path)
    source_url = extract_source_url(file_path)

    # Detect if file might contain multiple items
    is_multientry = any(kw in preview.lower() for kw in [
        "arxiv", "paper", "list", "summary", "newsletter", "digest",
        "bulletin", "weekly", "daily", "top", "most", "recent",
    ])

    if is_multientry:
        entry_count_hint = "\nExtract EACH distinct item as a separate entry."
    else:
        entry_count_hint = "\nReturn exactly ONE entry in the array."

    prompt = f"""You are an AI assistant analyzing research materials. Use concise Chinese.

返回格式 (JSON array, 不要代码块):
[
    {{
    "title": "document or item title",
    "title_cn": "标题中文翻译",
    "source_url": "url if available, else null",
    "domain": "所属领域 (e.g. 计算机视觉/3D重建/NLP)",
    "keywords": ["关键术语(中文)", "3-5个"],
    "match_level": "interested | possibly_interested | not_interested",
    "matched_interests": ["兴趣名称"],
    "reason": "why it matches (1-2 sentences)",
    "brief": "2-3 sentence summary",
    "detailed_report": "300-500 word Chinese report",
    "suggested_category": "papers | articles | talks | books | docs | projects | datasets"
  }}
]{entry_count_hint}

Current interests:
{interests_desc if interests_desc else "No specific interests defined."}

Document ({file_path.name}):
=== START ===
{preview}
=== END ===

Return ONLY the JSON array. No markdown fences, no prose.

如果下方「Current interests」为空，matched_interests 返回空数组 []。"""

    raw = None
    data = None
    try:
        raw = call_llm(prompt, max_tokens=4096)
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        clean = re.sub(r"\s*```$", "", clean.strip())
        data = json.loads(clean)
    except Exception as e:
        print(f"  ⚠️  LLM failed for {file_path.name}: {e}")
        if raw:
            print(f"  Raw (first 300): {raw[:300]}")

    if data is None:
        data = [{
            "item_id": 1,
            "match_level": "not_interested",
            "matched_interests": [],
            "reason": "LLM analysis failed",
            "brief": f"Unable to analyze '{file_path.name}'.",
            "detailed_report": f"LLM error. Raw: {raw[:500] if raw else 'API error'}",
            "title": file_path.stem,
            "source_url": source_url,
            "suggested_category": "papers",
        }]
    elif not isinstance(data, list):
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
            "title_cn": entry.get("title_cn", ""),
            "brief": entry.get("brief", ""),
            "detailed_report": entry.get("detailed_report", ""),
            "source_url": entry.get("source_url") or source_url,
            "domain": entry.get("domain", ""),
            "keywords": entry.get("keywords", []),
        })

    return results


def generate_brief_entries(results: list[dict], date_str: str = None) -> str:
    """Generate the brief.md content from analysis results."""
    today = date_str or date.today().isoformat()
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
                if date_str:
                    src_path = f"raw/digest/{date_str}/sources/{fname}"
                    lines.append(f"- 源文件: {src_path}")
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


def move_source(file_path: Path, date_str: str):
    """Move .md file + its images/ dir to digest/YYYY-MM-DD/sources/."""
    dest_dir = DIGEST_DIR / date_str / "sources"
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


def clear_inbox():
    """Clear inbox/ directory (keep inbox.md, empty its content)."""
    if not INBOX_DIR.exists():
        return
    inbox_files = list(INBOX_DIR.iterdir())
    if not inbox_files:
        print("  inbox/ 已为空。")
        return

    count = 0
    for f in inbox_files:
        if f.name == "inbox.md":
            f.write_text("# Inbox\n", encoding="utf-8")
            print("  📝 清空 inbox.md 内容")
            continue
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)
        count += 1
    print(f"  ✅ 已清空 inbox/ ({count} 个文件)")


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
    """Rebuild results list from cache, converting rel paths back to Path objects."""
    results = []
    for rel_path, entries in cache.items():
        abs_path = (REPO_ROOT / rel_path).resolve()
        for entry in entries:
            entry["file"] = abs_path
            results.append(entry)
    return results


def run_filter(dry_run: bool = False, json_output: bool = False):
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

    # Read interests
    interests = []
    interests_content = read_file(INTERESTS_FILE)
    if interests_content:
        interests = parse_interests(interests_content)
        print(f"读取到 {len(interests)} 个兴趣点。\n")
    else:
        print("  提示：wiki/interests.md 为空，仅生成摘要不匹配兴趣。\n")

    # Load checkpoint cache
    cache = load_filter_cache()
    skipped_from_cache = 0

    # Precompile interests_desc (same for all files)
    interests_desc = ""
    for interest in interests:
        kw_str = ", ".join(interest.get("keywords", []))
        interests_desc += f"- {interest['name']}:\n  - 权重: {interest.get('weight', 0.5)}\n  - 关键词: [{kw_str}]\n  - 描述: {interest.get('description', '')}\n"

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

    if pending:
        print(f"\n需分析 {len(pending)} 个文件（并行 max_workers=2）:\n")

        with ThreadPoolExecutor(max_workers=2) as exec:
            future_map = {
                exec.submit(analyze_file, fp, interests_desc): (fp, rel)
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
                    src = extract_source_url(fp)
                    fallback = [{
                        "file": rel,
                        "item_id": 1,
                        "match_level": "not_interested",
                        "matched_interests": [],
                        "reason": f"LLM failed: {e}",
                        "suggested_category": "papers",
                        "title": fp.stem,
                        "brief": f"Analysis failed for '{fp.name}'.",
                        "detailed_report": f"No report available.",
                        "source_url": src,
                    }]
                    cache[rel] = fallback
                    save_filter_cache(cache)
    else:
        print(f"\n所有文件均已缓存（{skipped_from_cache} 个）。")

    # Rebuild full results from cache
    results = rebuild_results_from_cache(cache)

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

    # Generate brief.md
    today = date.today().isoformat()
    brief_content = generate_brief_entries(results, today)

    if not dry_run:
        if BRIEF_FILE.exists():
            print("  正在归档旧 brief...")
            archive_current_brief()
            generate_new_brief()

        write_file(BRIEF_FILE, brief_content)

        for item in results:
            if item["file"].exists():
                print(f"  移动: {item['file'].name} → {today}/sources/")
                try:
                    source_dest = move_source(item["file"], today)
                    print(f"    ✅ {source_dest}")
                except Exception as e:
                    print(f"    ⚠️  move failed: {e}")

        clear_inbox()

        # Clear checkpoint cache
        if FILTER_CACHE.exists():
            FILTER_CACHE.unlink()
            print("  🧹 已清理缓存")

    # Log
    log_entry = f"## [{date.today().isoformat()}] filter | {len(results)} files processed"
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

    print(f"\n✅ 筛选完成！报告已保存到: {BRIEF_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and classify files in raw/inbox/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without moving files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--clear-cache", action="store_true", help="Clear checkpoint cache and re-analyze all files")
    args = parser.parse_args()

    if args.clear_cache:
        if FILTER_CACHE.exists():
            FILTER_CACHE.unlink()
            print("🧹 缓存已清理")
        else:
            print("缓存不存在，无需清理")
        sys.exit(0)

    run_filter(dry_run=args.dry_run, json_output=args.json)
