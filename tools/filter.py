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
    """Parse interests/disinterests from wiki/interests.md content.

    Format:
        ## 兴趣列表
        - 名称 [kw1, kw2, ...]
        - 名称

        ## 排除列表
        - 名称 [kw1, kw2, ...]
    """
    entries = []
    current_category = None
    VALID_SECTIONS = {"兴趣列表", "排除列表"}

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        cat_match = re.match(r'^## (.+)$', line)
        if cat_match:
            current_category = cat_match.group(1).strip() if cat_match.group(1).strip() in VALID_SECTIONS else None
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
            })

    return entries


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


def analyze_file(file_path: Path, interests_desc: str, disinterests_desc: str = "") -> list[dict]:
    """Use LLM to analyze file. interests_desc/disinterests_desc precompiled from run_filter()."""
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
    "brief": "brief summary (if not_interested, keep to 1 sentence)",
    "detailed_report": "300-500 word Chinese report (if not_interested, set to empty string)",
    "suggested_category": "papers | articles | talks | books | docs | projects | datasets",
    "suggested_new_interests": [{{"name": "...", "weight": 0.8, "keywords": ["..."], "description": "..."}}],
    "suggested_new_disinterests": [{{"name": "...", "weight": 0.9, "keywords": ["..."], "description": "..."}}]
  }}
]{entry_count_hint}

Current interests:
{interests_desc if interests_desc else "No specific interests defined."}

Exclusion list (if document matches any of these, MUST set match_level to "not_interested"):
{disinterests_desc if disinterests_desc else "None defined."}

Document ({file_path.name}):
=== START ===
{preview}
=== END ===

Return ONLY the JSON array. No markdown fences, no prose.

如果「Current interests」为空，matched_interests 返回空数组 []。
如果文档涉及的兴趣/排除项不在上方列表中，可建议新增到 suggested_new_interests / suggested_new_disinterests（可选）。"""

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
        raise RuntimeError(f"LLM analysis failed for {file_path.name}")
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
            "title_cn": entry.get("title_cn", ""),
            "brief": entry.get("brief", ""),
            "detailed_report": entry.get("detailed_report", ""),
            "source_url": entry.get("source_url") or source_url,
            "domain": entry.get("domain", ""),
            "keywords": entry.get("keywords", []),
            "suggested_new_interests": entry.get("suggested_new_interests", []),
            "suggested_new_disinterests": entry.get("suggested_new_disinterests", []),
        })

    return results


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


def clear_inbox(skip_rel_paths: set[str] | None = None):
    """Clear inbox/ directory (keep inbox.md, empty its content). Keep files in skip_rel_paths."""
    if not INBOX_DIR.exists():
        return
    inbox_files = list(INBOX_DIR.iterdir())
    if not inbox_files:
        print("  inbox/ 已为空。")
        return

    skipped = set()
    if skip_rel_paths:
        # convert rel paths to just filenames for comparison
        skipped = {Path(p).name for p in skip_rel_paths}

    count = 0
    for f in inbox_files:
        if f.name == "inbox.md":
            f.write_text("# Inbox\n", encoding="utf-8")
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
        disinterests_desc += f"- {d['name']}:\n  - 关键词: [{kw_str}]\n  - 描述: {d.get('description', '')}\n"

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

    if pending:
        print(f"\n需分析 {len(pending)} 个文件（并行 max_workers=2）:\n")

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
    disinterested_count = 0
    disinterest_keywords = set()
    for d in disinterests:
        disinterest_keywords.update(k.lower() for k in d.get("keywords", []))
    if disinterest_keywords:
        for r in results:
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

    # Generate brief.md (only successful entries)
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
            kw = ", ".join(si.get("keywords", []))
            print(f"  - {si['name']} (权重: {si.get('weight', 0.5)}) [{kw}]")
    if suggested_disinterests:
        print("\n🚫 建议新增排除项:")
        for sd in suggested_disinterests:
            kw = ", ".join(sd.get("keywords", []))
            print(f"  - {sd['name']} (权重: {sd.get('weight', 0.9)}) [{kw}]")
    if disinterested_count:
        print(f"\n  🚫 排除列表命中: {disinterested_count} 个文件未写入 brief")
    print(f"\n✅ 筛选完成！报告已保存到: {BRIEF_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter and classify files in raw/inbox/")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without moving files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--clear-cache", action="store_true", help="Clear checkpoint cache and re-analyze all files")
    parser.add_argument("--retry-failed", action="store_true", help="Re-process files listed in raw/.filter-failed.txt")
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

    run_filter(dry_run=args.dry_run, json_output=args.json)
