#!/usr/bin/env python3
"""
Bookmark Processing Tracker — 记录 Edge 书签的 wiki 处理状态。

Usage:
    python tools/bookmark-tracker.py              # 打印报告
    python tools/bookmark-tracker.py --update     # 更新 raw/inbox/bookmark-tracker.md
    python tools/bookmark-tracker.py --json       # 输出 JSON
    python tools/bookmark-tracker.py --archive    # 只检查 Inbox Archive
    python tools/bookmark-tracker.py --inbox      # 只检查 Inbox
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent

BOOKMARKS_PATH = Path(os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Bookmarks"
))

TRACKER_FILE = REPO_ROOT / "raw" / "inbox" / "bookmark-tracker.md"

# ── Helpers ─────────────────────────────────────────────────────────────

def find_folder(node, parts):
    if not parts:
        return node
    t = parts[0]
    for c in node.get("children", []):
        if c.get("type") == "folder" and c.get("name") == t:
            return find_folder(c, parts[1:])
    return None


def collect_urls(node):
    urls = []
    for c in node.get("children", []):
        if c.get("type") == "url":
            urls.append({"name": c.get("name", ""), "url": c.get("url", "")})
        elif c.get("type") == "folder":
            urls.extend(collect_urls(c))
    return urls


def norm_url(url):
    """Normalize URL for comparison (strip query params, trailing /, protocol)."""
    u = url.strip().rstrip(")").rstrip("]").rstrip(">")
    # Strip utm_* params
    u = re.sub(r'\?utm_.*', '', u)
    u = re.sub(r'\?chatId=.*', '', u)
    # Remove query entirely for arxiv
    u = u.split("?")[0].rstrip("/").lower()
    return u


def extract_arxiv_id(url):
    m = re.search(r'arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5}(?:v\d+)?)', url)
    if m:
        return m.group(1)
    m = re.search(r'alphaxiv\.org/.*?(\d{4}\.\d{4,5}(?:v\d+)?)', url)
    if m:
        return m.group(1)
    return None


# ── Build lookup indices from wiki state ─────────────────────────────────

def build_wiki_index():
    """Build lookup sets for fast cross-referencing."""
    index = {
        "in_inbox_md": set(),       # normalized URLs in inbox.md
        "in_brief": set(),          # normalized URLs in brief
        "in_brief_deepread": set(), # titles/urls checked deep-read
        "in_brief_ingest": set(),   # titles/urls checked ingest
        "in_brief_skip": set(),     # titles/urls checked skip
        "in_wiki_log": set(),       # titles from log.md (ingested)
        "in_wiki_source": set(),    # normalized URLs from wiki source pages
        "in_deepdive": set(),       # titles from deepdive files
        "all_log_text": "",         # full log text for title matching
    }

    # inbox.md
    inbox_path = REPO_ROOT / "raw" / "inbox" / "inbox.md"
    if inbox_path.exists():
        text = inbox_path.read_text(encoding="utf-8")
        for m in re.finditer(r'https?://\S+', text):
            index["in_inbox_md"].add(norm_url(m.group(0)))

    # brief files
    brief_dir = REPO_ROOT / "raw" / "digest" / "brief"
    brief_main = REPO_ROOT / "raw" / "digest" / "brief.md"
    brief_texts = []
    if brief_main.exists():
        brief_texts.append(brief_main.read_text(encoding="utf-8"))
    if brief_dir.exists():
        for f in sorted(brief_dir.glob("*.md")):
            brief_texts.append(f.read_text(encoding="utf-8"))

    for text in brief_texts:
        # URLs
        for m in re.finditer(r'- 来源:\s*(https?://\S+)', text):
            index["in_brief"].add(norm_url(m.group(1)))
        # Checkboxes
        titles = re.findall(r'^#### (.+)', text, re.MULTILINE)
        # Track checkboxes by proximity to title
        sections = re.split(r'^#### ', text, flags=re.MULTILINE)[1:]
        for sec in sections:
            title = sec.split('\n')[0].strip()
            title_lower = title.lower()
            has_deepread = '[x] 深度阅读' in sec.lower()
            has_ingest = '[x] 合入 wiki' in sec.lower()
            has_skip = '[x] 不感兴趣' in sec.lower()
            if has_deepread:
                index["in_brief_deepread"].add(title_lower)
            if has_ingest:
                index["in_brief_ingest"].add(title_lower)
            if has_skip:
                index["in_brief_skip"].add(title_lower)

    # log.md
    log_path = REPO_ROOT / "wiki" / "log.md"
    if log_path.exists():
        index["all_log_text"] = log_path.read_text(encoding="utf-8")
        # Ingest entries
        for m in re.finditer(r'\[[\d\-]+\]\s*ingest\s*\|\s*(.+)', index["all_log_text"]):
            index["in_wiki_log"].add(m.group(1).strip().lower())

    # wiki sources — check content for URLs
    sources_dir = REPO_ROOT / "wiki" / "sources"
    if sources_dir.exists():
        for f in sources_dir.glob("*.md"):
            text = f.read_text(encoding="utf-8")
            for m in re.finditer(r'https?://\S+', text):
                index["in_wiki_source"].add(norm_url(m.group(0)))
            index["in_wiki_source"].add(f.stem.lower())

    # deepdive files
    deepdive_dir = REPO_ROOT / "raw" / "digest" / "deepdive"
    if deepdive_dir.exists():
        for f in deepdive_dir.rglob("*.md"):
            index["in_deepdive"].add(f.stem.lower().replace("-", " "))

    return index


# ── Determine processing status ──────────────────────────────────────────

def determine_status(item, index):
    """Determine processing status of a bookmark item."""
    name = item["name"]
    url = item["url"]
    normed = norm_url(url)
    arxiv_id = extract_arxiv_id(url)
    name_lower = name.lower()

    result = {
        "name": name,
        "url": url,
        "status": "⏳ 未导入",
        "in_inbox_md": normed in index["in_inbox_md"],
        "in_brief": False,
        "in_brief_deepread": False,
        "in_brief_ingest": False,
        "in_brief_skip": False,
        "in_wiki_log": False,
        "in_wiki_source": False,
        "in_deepdive": False,
        "detail": "",
    }

    # Check brief
    # Match by URL or arxiv ID
    brief_url_match = False
    for brief_u in index["in_brief"]:
        if normed == brief_u or (arxiv_id and arxiv_id in brief_u):
            brief_url_match = True
            break
    # Also try matching by title
    brief_title_match = False
    for idx_name in list(index["in_brief_deepread"]) + list(index["in_brief_ingest"]) + list(index["in_brief_skip"]):
        words = name_lower.split()[:5]  # first 5 words
        if any(w in idx_name for w in words if len(w) > 3):
            brief_title_match = True
            break

    result["in_brief"] = brief_url_match or brief_title_match
    if result["in_brief"]:
        # Check specific checkboxes
        for bd in index["in_brief_deepread"]:
            if any(w in bd for w in name_lower.split()[:5] if len(w) > 3):
                result["in_brief_deepread"] = True
                break
        for bi in index["in_brief_ingest"]:
            if any(w in bi for w in name_lower.split()[:5] if len(w) > 3):
                result["in_brief_ingest"] = True
                break
        for bs in index["in_brief_skip"]:
            if any(w in bs for w in name_lower.split()[:5] if len(w) > 3):
                result["in_brief_skip"] = True
                break

    # Check wiki log — match by title keywords
    for log_item in index["in_wiki_log"]:
        log_words = log_item.split()[:5]
        if any(w in name_lower for w in log_words if len(w) > 4):
            result["in_wiki_log"] = True
            break
    # Also match by arxiv ID in log
    if arxiv_id and arxiv_id in index["all_log_text"]:
        result["in_wiki_log"] = True

    # Check wiki sources
    if normed in index["in_wiki_source"] or name_lower in index["in_wiki_source"]:
        result["in_wiki_source"] = True
    if arxiv_id:
        for s in index["in_wiki_source"]:
            if arxiv_id in s:
                result["in_wiki_source"] = True
                break
    # Check source file stem
    stem = re.sub(r'[^a-z0-9]+', '-', name_lower).strip('-')
    if stem in index["in_wiki_source"]:
        result["in_wiki_source"] = True

    # Check deepdive
    for dd in index["in_deepdive"]:
        if any(w in dd for w in name_lower.split()[:5] if len(w) > 4):
            result["in_deepdive"] = True
            break

    # Determine composite status
    if result["in_wiki_source"]:
        result["status"] = "✅ 已合入"
        result["detail"] = "wiki 页面已创建"
    elif result["in_brief_skip"]:
        result["status"] = "⏭️ 已跳过"
        result["detail"] = "简报中标记为不感兴趣"
    elif result["in_deepdive"]:
        result["status"] = "📖 已深读未合入"
        result["detail"] = "深度阅读已生成，未合入 wiki"
    elif result["in_brief_ingest"]:
        result["status"] = "📋 已标记合入"
        result["detail"] = "简报中已勾选合入但尚未执行"
    elif result["in_brief_deepread"]:
        result["status"] = "🔍 已标记深读"
        result["detail"] = "简报中已勾选深度阅读但尚未生成"
    elif result["in_brief"]:
        result["status"] = "📄 已简报"
        result["detail"] = "已在简报中但未做任何标记"
    elif result["in_inbox_md"]:
        result["status"] = "📥 在 inbox.md 中"
        result["detail"] = "已导入 inbox.md 但尚未筛选"
    else:
        result["status"] = "⏳ 未导入"
        result["detail"] = "尚未导入 wiki 流程"

    return result


# ── Report generation ───────────────────────────────────────────────────

def generate_tracker(bookmark_paths=None, archive_only=False, inbox_only=False):
    """Generate tracking data."""
    if not BOOKMARKS_PATH.exists():
        print(f"❌ Edge 书签文件未找到: {BOOKMARKS_PATH}")
        sys.exit(1)

    data = json.loads(BOOKMARKS_PATH.read_text(encoding="utf-8"))
    root = data["roots"]["bookmark_bar"]

    index = build_wiki_index()

    folders = []
    if inbox_only:
        folders.append(("Wiki/Inbox",  "📥 待导入"))
    elif archive_only:
        folders.append(("Wiki/Inbox Archive", "🗂️ 已归档"))
    else:
        folders = [
            ("Wiki/Inbox",           "📥 待导入"),
            ("Wiki/Inbox Archive",   "🗂️ 已归档"),
        ]

    results = []
    for fp, label in folders:
        parts = [p for p in fp.split("/") if p]
        folder = find_folder(root, parts)
        if not folder:
            continue
        urls = collect_urls(folder)
        items = []
        for u in urls:
            item = determine_status(u, index)
            item["folder"] = fp
            item["folder_label"] = label
            items.append(item)
        results.append((fp, label, items))

    return results


def print_report(results):
    """Print human-readable report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"# Edge 书签处理状态报告  ({now})\n")

    for fp, label, items in results:
        print(f"## {label}: {fp} ({len(items)} 条)\n")
        if not items:
            print("  (空)\n")
            continue

        # Status summary
        status_counts = {}
        for item in items:
            s = item["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
        summary = "  ".join(f"{k}: {v}" for k, v in sorted(status_counts.items()))
        print(f"  状态汇总: {summary}\n")

        # Detail table
        for i, item in enumerate(items, 1):
            print(f"  {i:2d}. {item['status']} {item['name']}")
            if item["detail"]:
                print(f"      ↳ {item['detail']}")
            print(f"      {item['url']}")
            print()

    # Overall stats
    total = sum(len(items) for _, _, items in results)
    processed = sum(
        1 for _, _, items in results
        for item in items
        if item["status"] in ("✅ 已合入", "⏭️ 已跳过", "📖 已深读未合入", "📋 已标记合入")
    )
    pending = total - processed
    print(f"---\n总计: {total}  已处理: {processed}  待处理: {pending}")


def update_tracker_file(results):
    """Write the tracking record to bookmark-tracker.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["# 书签处理记录", "", f"> 自动生成于 {now}。运行 `python tools/bookmark-tracker.py --update` 刷新。", ""]

    for fp, label, items in results:
        lines.append(f"## {label}: {fp}")
        lines.append("")
        if not items:
            lines.append("_（空）_")
            lines.append("")
            continue

        lines.append("| # | 标题 | 状态 | 来源 | 简报 | 深读 | 合入 | 备注 |")
        lines.append("|---|------|------|------|------|------|------|------|")

        for i, item in enumerate(items, 1):
            name = item["name"]
            url = item["url"]
            status = item["status"]
            source = "arXiv" if "arxiv" in url else "其他"

            brief_mark = "✅" if item["in_brief"] else ("⬜" if item["in_inbox_md"] else "—")
            deepread_mark = "✅" if item["in_deepdive"] else ("🔄" if item["in_brief_deepread"] else "—")
            ingest_mark = "✅" if item["in_wiki_source"] else ("🔄" if item["in_brief_ingest"] else "—")
            detail = item["detail"]

            # Escape | in name
            name_escaped = name.replace("|", "\\|")
            lines.append(
                f"| {i} | {name_escaped} | {status} | {source} | {brief_mark} | {deepread_mark} | {ingest_mark} | {detail} |"
            )

        lines.append("")

    # Status legend
    lines.extend([
        "---",
        "### 图例",
        "- **状态**: ✅ 已合入 / ⏭️ 已跳过 / 📖 已深读 / 📋 已标记合入 / 📄 已简报 / 📥 在 inbox.md / ⏳ 未导入",
        "- **简报**: ✅ 在简报中 / ⬜ 在 inbox.md 中 / — 未进入流程",
        "- **深读**: ✅ 已生成深度阅读 / 🔄 已勾选待生成 / — 无",
        "- **合入**: ✅ 已合入 wiki / 🔄 已勾选待合入 / — 无",
        "",
    ])

    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ 已更新跟踪记录: {TRACKER_FILE}")


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Edge 书签 wiki 处理状态跟踪")
    parser.add_argument("--update", action="store_true", help="更新 bookmark-tracker.md")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--archive", action="store_true", help="只检查 Inbox Archive")
    parser.add_argument("--inbox", action="store_true", help="只检查 Inbox")
    args = parser.parse_args()

    results = generate_tracker(
        archive_only=args.archive,
        inbox_only=args.inbox,
    )

    if args.json:
        output = []
        for fp, label, items in results:
            output.append({"folder": fp, "label": label, "items": items})
        print(json.dumps(output, indent=2, ensure_ascii=False))
    elif args.update:
        update_tracker_file(results)
        # Also print summary
        print()
        print_report(results)
    else:
        print_report(results)


if __name__ == "__main__":
    main()
