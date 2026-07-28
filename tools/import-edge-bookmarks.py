#!/usr/bin/env python3
"""
Import bookmarks from Edge browser to inbox.md.

Usage:
    python tools/import-edge-bookmarks.py                     # 导入 → 去重 → 归档（默认）
    python tools/import-edge-bookmarks.py "Wiki/Inbox"        # 自定义文件夹
    python tools/import-edge-bookmarks.py --list               # 列出所有文件夹
    python tools/import-edge-bookmarks.py --import-only        # 仅导入，不去重不归档
    python tools/import-edge-bookmarks.py --no-dedup           # 导入+归档，跳过去重
    python tools/import-edge-bookmarks.py --no-archive         # 导入+去重，跳过归档
    python tools/import-edge-bookmarks.py --archive            # 仅归档
    python tools/import-edge-bookmarks.py --profile "Profile 1"  # 非默认 profile

Folder path uses '/' separator, e.g. "Wiki/Inbox" or "收藏夹栏/参考".
Roots: bookmark_bar (default), other, synced.
"""

import json
import sys
import re
import argparse
import os
import shutil
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
INBOX_DIR = REPO_ROOT / "raw" / "inbox"
INBOX_MD = INBOX_DIR / "inbox.md"
BOOKMARKS_PATH = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Bookmarks"))


def find_bookmarks_file(profile: str = "Default") -> Path:
    p = Path(os.path.expandvars(rf"%LOCALAPPDATA%\Microsoft\Edge\User Data\{profile}\Bookmarks"))
    if p.exists():
        return p
    raise FileNotFoundError(f"Bookmarks file not found: {p}")


def find_folder(node: dict, path_parts: list[str]) -> dict | None:
    """Recursively find a folder node by path parts."""
    if not path_parts:
        return node
    target = path_parts[0]
    for child in node.get("children", []):
        if child.get("type") == "folder" and child.get("name") == target:
            return find_folder(child, path_parts[1:])
    return None


def find_or_create_folder(parent: dict, folder_name: str) -> dict:
    """Find or create a folder under parent node."""
    for child in parent.get("children", []):
        if child.get("type") == "folder" and child.get("name") == folder_name:
            return child
    new_folder = {
        "children": [],
        "date_added": "0",
        "date_last_used": "0",
        "date_modified": "0",
        "guid": "",
        "id": "",
        "name": folder_name,
        "type": "folder",
    }
    parent.setdefault("children", []).append(new_folder)
    return new_folder


def collect_urls(node: dict) -> list[dict]:
    """Collect all url bookmarks from a folder tree."""
    urls = []
    for child in node.get("children", []):
        if child.get("type") == "url":
            urls.append({
                "name": child.get("name", ""),
                "url": child.get("url", ""),
                "date_added": child.get("date_added", ""),
            })
        elif child.get("type") == "folder":
            urls.extend(collect_urls(child))
    return urls


def list_folders(node: dict, prefix: str = "", depth: int = 0, max_depth: int = 4):
    """Print folder tree."""
    if depth > max_depth:
        return
    for child in node.get("children", []):
        if child.get("type") == "folder":
            name = child.get("name", "?")
            url_count = sum(1 for c in child.get("children", []) if c.get("type") == "url")
            print(f"{'  ' * depth}{prefix}{name}/ ({url_count} links)")
            list_folders(child, prefix, depth + 1, max_depth)


def write_inbox(urls: list[dict], append: bool = True):
    """Write URLs to inbox.md, one per line as markdown links."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing inbox.md to avoid duplicates
    existing_urls = set()
    existing_content = ""
    if append and INBOX_MD.exists():
        existing_content = INBOX_MD.read_text(encoding="utf-8")
        existing_urls = set(re.findall(r'https?://\S+', existing_content))

    new_lines = []
    added = 0
    for item in urls:
        url = item["url"]
        name = item["name"]
        if url not in existing_urls:
            new_lines.append(f"- [{name}]({url})")
            existing_urls.add(url)
            added += 1

    if not new_lines:
        print("所有书签已在 inbox.md 中，无需添加。")
        return

    if append and existing_content.strip() and existing_content.strip() != "# Inbox":
        content = existing_content.rstrip() + "\n" + "\n".join(new_lines) + "\n"
    else:
        content = "# Inbox\n\n" + "\n".join(new_lines) + "\n"

    INBOX_MD.write_text(content, encoding="utf-8")
    print(f"✅ 已添加 {added} 个链接到 inbox.md（共 {len(urls)} 个，去重后 {added} 个新链接）")


def dedup_inbox_md():
    """Deduplicate inbox.md by arxiv ID and rewrite the file.

    Imports dedup logic from inbox.py to keep behavior consistent.
    """
    if not INBOX_MD.exists():
        print("inbox.md 不存在，跳过去重。")
        return

    # Import dedup from inbox.py
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from inbox import read_inbox_md, INBOX_MD as _  # noqa

    items = read_inbox_md()
    if not items:
        print("inbox.md 为空。")
        return

    before = len(INBOX_MD.read_text(encoding="utf-8").strip().splitlines()) - 1
    lines = ["# Inbox", ""]

    for item in items:
        related = item.get("related_urls", [])
        link = item["link"]
        raw = item.get("raw", "")
        md_match = re.search(r'\[(.+?)\]\(', raw)
        title = md_match.group(1) if md_match else link
        lines.append(f"- [{title}]({link})")
        if related:
            parts = [f"[{r['type']}]({r['url']})" for r in related]
            lines.append(f"  - related: {', '.join(parts)}")

    lines.append("")
    INBOX_MD.write_text("\n".join(lines), encoding="utf-8")
    after = len(items)
    print(f"✅ inbox.md 已去重: {before} 行 → {after} 条独立条目")


def archive_bookmarks(data: dict, source_path: str, archive_path: str, urls_to_archive: list[str] | None = None):
    """Move bookmarks from source folder to archive folder in the bookmarks tree.

    Args:
        data: Full bookmarks JSON data (will be modified in place).
        source_path: Source folder path, e.g. "Wiki/Inbox".
        archive_path: Archive folder path, e.g. "Wiki/Inbox Archive".
        urls_to_archive: If provided, only archive these URLs. If None, archive all.
    """
    source_parts = [p for p in source_path.replace("\\", "/").split("/") if p]
    archive_parts = [p for p in archive_path.replace("\\", "/").split("/") if p]

    # Find source folder in bookmark_bar
    root = data["roots"]["bookmark_bar"]
    source_folder = find_folder(root, source_parts)
    if not source_folder:
        print(f"❌ 源文件夹 '{source_path}' 不存在")
        return 0

    # Find or create archive folder
    # Navigate to parent of archive, creating intermediates as needed
    archive_parent_parts = archive_parts[:-1]
    archive_name = archive_parts[-1]
    archive_parent = find_folder(root, archive_parent_parts) if archive_parent_parts else root
    if not archive_parent:
        print(f"❌ 归档父文件夹 '{'/'.join(archive_parts)}' 不存在")
        return 0
    archive_folder = find_or_create_folder(archive_parent, archive_name)

    # Create a date-stamped subfolder inside the archive folder
    today = datetime.now().strftime("%Y-%m-%d")
    date_folder = find_or_create_folder(archive_folder, today)

    # Determine which bookmarks to move
    children = source_folder.get("children", [])
    to_move = []
    remaining = []

    if urls_to_archive:
        # Normalize URLs for prefix matching (strip query params and trailing slashes)
        def _norm(url: str) -> str:
            return url.split("?")[0].rstrip("/").lower()

        url_norms = {_norm(u): u for u in urls_to_archive}
        for child in children:
            if child.get("type") == "url":
                child_norm = _norm(child.get("url", ""))
                if child_norm in url_norms:
                    to_move.append(child)
                else:
                    remaining.append(child)
            else:
                remaining.append(child)
    else:
        to_move = [c for c in children if c.get("type") == "url"]
        remaining = [c for c in children if c.get("type") != "url"]

    if not to_move:
        print("没有需要归档的书签。")
        return 0

    # Move bookmarks into the date-stamped subfolder
    for bookmark in to_move:
        date_folder.setdefault("children", []).append(bookmark)

    # Keep only non-url children (subfolders) in source
    source_folder["children"] = remaining

    archive_path_full = f"{archive_path}/{today}"
    print(f"✅ 已归档 {len(to_move)} 个书签: {source_path} → {archive_path_full}")
    return len(to_move)


def archive_from_brief(data: dict, source_path: str, archive_path: str):
    """Archive bookmarks whose URLs appear in brief.md (already processed)."""
    if not INBOX_MD.exists():
        print("inbox.md 不存在，跳过归档。")
        return 0

    content = INBOX_MD.read_text(encoding="utf-8")
    urls = re.findall(r'https?://\S+', content)
    if not urls:
        print("inbox.md 中无链接。")
        return 0

    print(f"从 inbox.md 读取 {len(urls)} 个链接用于归档")
    return archive_bookmarks(data, source_path, archive_path, urls)


def main():
    parser = argparse.ArgumentParser(description="Import Edge bookmarks to inbox.md")
    parser.add_argument("folder", nargs="?", default="Wiki/Inbox",
                        help="Folder path in bookmarks (default: Wiki/Inbox)")
    parser.add_argument("--list", action="store_true", help="List all bookmark folders")
    parser.add_argument("--profile", default="Default", help="Edge profile name")
    parser.add_argument("--root", default="bookmark_bar",
                        choices=["bookmark_bar", "other", "synced"],
                        help="Bookmark root (default: bookmark_bar)")
    parser.add_argument("--no-append", action="store_true", help="Overwrite inbox.md instead of appending")
    parser.add_argument("--import-only", action="store_true",
                        help="Only import, skip dedup and archive")
    parser.add_argument("--no-dedup", action="store_true",
                        help="Import + archive, skip dedup")
    parser.add_argument("--no-archive", action="store_true",
                        help="Import + dedup, skip archive")
    parser.add_argument("--archive", action="store_true",
                        help="Archive only: move bookmarks to Archive folder")
    parser.add_argument("--archive-url", action="append", default=[],
                        help="Archive specific URL(s) from the source folder (can repeat)")
    parser.add_argument("--archive-from", default=None,
                        help="Archive URL list from this file (one URL per line)")
    parser.add_argument("--archive-to", default=None,
                        help="Archive destination folder (default: <source> Archive/)")
    args = parser.parse_args()

    try:
        bookmarks_file = find_bookmarks_file(args.profile)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    with open(bookmarks_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    roots = data.get("roots", {})
    root_node = roots.get(args.root)
    if not root_node:
        print(f"❌ Root '{args.root}' not found in bookmarks")
        sys.exit(1)

    # List mode
    if args.list:
        print(f"=== {args.root} ===")
        list_folders(root_node)
        return

    # Archive-only mode
    if args.archive or args.archive_url or args.archive_from:
        archive_dest = args.archive_to or f"{args.folder} Archive"
        urls_to_archive = list(args.archive_url)

        if args.archive_from:
            archive_file = Path(args.archive_from)
            if archive_file.exists():
                file_urls = [line.strip() for line in archive_file.read_text(encoding="utf-8").splitlines()
                             if line.strip() and line.strip().startswith("http")]
                urls_to_archive.extend(file_urls)
            else:
                print(f"⚠️  归档文件不存在: {args.archive_from}")

        if urls_to_archive:
            count = archive_bookmarks(data, args.folder, archive_dest, urls_to_archive)
        elif args.archive and not args.archive_from:
            count = archive_bookmarks(data, args.folder, archive_dest, urls_to_archive=None)
        else:
            count = 0

        if count > 0:
            tmp_file = bookmarks_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=3)
            shutil.move(str(tmp_file), str(bookmarks_file))
            print(f"📝 Edge 书签文件已更新: {bookmarks_file}")
            print("⚠️  请重启 Edge 浏览器使更改生效。")
        return

    # ── Default: import → dedup → archive ──
    # Step 0: find folder
    parts = [p for p in args.folder.replace("\\", "/").split("/") if p]
    folder = find_folder(root_node, parts)
    if not folder:
        print(f"❌ Folder '{args.folder}' not found")
        print("Use --list to see available folders.")
        sys.exit(1)

    urls = collect_urls(folder)
    if not urls:
        print(f"文件夹 '{args.folder}' 为空。")
        return

    # Step 1: import
    print(f"━━━ Step 1/3: 导入书签 ━━━")
    print(f"从 '{args.folder}' 找到 {len(urls)} 个链接")
    write_inbox(urls, append=not args.no_append)

    # Step 2: dedup (skip if --no-dedup or --import-only)
    if not args.no_dedup and not args.import_only:
        print(f"\n━━━ Step 2/3: 去重 ━━━")
        dedup_inbox_md()
    else:
        print(f"\n━━━ Step 2/3: 去重 (跳过) ━━━")

    # Step 3: archive (skip if --no-archive or --import-only)
    archived = 0
    if not args.no_archive and not args.import_only:
        print(f"\n━━━ Step 3/3: 归档书签 ━━━")
        archive_dest = args.archive_to or f"{args.folder} Archive"
        archived = archive_bookmarks(data, args.folder, archive_dest, urls_to_archive=None)
        if archived > 0:
            tmp_file = bookmarks_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=3)
            shutil.move(str(tmp_file), str(bookmarks_file))
            print(f"📝 Edge 书签文件已更新")
            print("⚠️  请重启 Edge 浏览器使更改生效。")
    else:
        print(f"\n━━━ Step 3/3: 归档书签 (跳过) ━━━")

    print(f"\n✅ 完成: {len(urls)} 导入 → {archived} 归档")


if __name__ == "__main__":
    main()
