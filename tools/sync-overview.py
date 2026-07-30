#!/usr/bin/env python3
"""
Auto-generate wiki/overview.md from wiki/index.md source entries.

Deterministic (no LLM calls). Groups source entries by logical categories
based on keywords. Designed to be called from health.py auto-fix.

Usage:
    python tools/sync-overview.py              # print to stdout
    python tools/sync-overview.py --write      # overwrite wiki/overview.md
    python tools/sync-overview.py --check      # exit 1 if out of sync
"""

import re
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
OVERVIEW_FILE = WIKI_DIR / "overview.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_index_sources(content: str) -> dict[str, list[tuple[str, str, str]]]:
    """Parse entries under sections like ## Papers / ## Sources / ## Articles.

    Returns dict: section_name -> [(title, path, summary)]
    Deduplicates by path (slug).
    """
    sections = {}
    current_section = None
    seen_slugs = set()

    line_iter = iter(content.split("\n"))
    for line in line_iter:
        m = re.match(r'^## (.+)$', line.strip())
        if m:
            current_section = m.group(1).strip()
            continue

        entry_m = re.match(r'^- \[(.+?)\]\(([^)]+)\)\s*—\s*(.*)', line.strip())
        if entry_m and current_section:
            title = entry_m.group(1).strip()
            path = entry_m.group(2).strip()
            summary = entry_m.group(3).strip()

            # Only include source/entity/concept pages
            if not (path.startswith("sources/") or path.startswith("entities/") or path.startswith("concepts/")):
                continue

            # Deduplicate by slug
            slug = Path(path).stem
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            sections.setdefault(current_section, []).append((title, path, summary))

    return sections


_SECTION_CATEGORY_MAP: dict[str, str] = {
    "Papers": "论文",
    "Articles": "文章",
    "Books": "书籍",
    "Projects": "项目",
    "Talks": "演讲",
    "Datasets": "数据集",
    "Docs": "文档",
    "Sources": "其他源",
}

# Group some known sections together
_CATEGORY_ORDER = [
    "论文",
    "文章",
    "项目",
    "数据集",
    "文档",
    "其他源",
]


def categorize_section(header: str) -> str:
    """Map index section headers to overview categories."""
    return _SECTION_CATEGORY_MAP.get(header, "其他")


def build_overview(index_content: str) -> str:
    """Generate overview.md content from index.md entries."""
    sections = parse_index_sources(index_content)

    # Group by overview category
    categorized: dict[str, list[tuple[str, str, str]]] = {}
    for section_header, entries in sections.items():
        cat = categorize_section(section_header)
        categorized.setdefault(cat, []).extend(entries)

    lines = [
        "---",
        "title: \"Overview\"",
        "type: synthesis",
        "tags: []",
        "sources: []",
        "last_updated: \"__TODAY__\"",
        "---",
        "",
        "# Overview",
        "",
        "当前 wiki 包含以下已合入的源文档：",
        "",
    ]

    for cat in _CATEGORY_ORDER:
        entries = categorized.pop(cat, None)
        if not entries:
            continue

        # Sort by title
        entries_sorted = sorted(entries, key=lambda x: x[0].lower())

        lines.append(f"### {cat}")
        lines.append("")
        for title, path, summary in entries_sorted:
            lines.append(f"- [[{title}|{Path(path).stem}]] — {summary}")
        lines.append("")

    # Remaining uncategorized groups
    for cat, entries in sorted(categorized.items()):
        lines.append(f"### {cat}")
        lines.append("")
        for title, path, summary in sorted(entries, key=lambda x: x[0].lower()):
            lines.append(f"- [[{title}|{Path(path).stem}]] — {summary}")
        lines.append("")

    return "\n".join(lines)


def get_current_overview_slugs(content: str) -> set[str]:
    """Extract slugs referenced in overview.md."""
    slugs = set()
    for m in re.finditer(r'\[\[([^\]|]+)(?:\|[^\]|]+)?\]\]', content):
        slug = m.group(1).strip()
        if slug:
            slugs.add(slug.lower())
    return slugs


def _extract_manual_sections(existing: str, new_slugs: set[str]) -> str:
    """Extract sections from existing overview whose wikilinks aren't in new_slugs.

    A "section" is the content under a `###` header. Sections whose ALL wikilinks
    are absent from new_slugs are considered manual additions and returned.
    """
    lines = existing.split('\n')
    sections = []
    current_header = None
    current_lines = []
    current_slugs = set()

    def _flush():
        nonlocal current_header, current_lines, current_slugs
        if current_header and current_lines:
            has_orphan = current_slugs and current_slugs.isdisjoint(new_slugs)
            has_no_links = not current_slugs
            if has_orphan or has_no_links:
                sections.append('\n'.join([current_header] + current_lines))
        current_header = None
        current_lines = []
        current_slugs = set()

    for line in lines:
        if line.startswith('### '):
            _flush()
            current_header = line
        elif current_header:
            current_lines.append(line)
            for m in re.finditer(r'\[\[([^\]|]+)(?:\|[^\]|]+)?\]\]', line):
                current_slugs.add(m.group(1).strip().lower())

    _flush()
    return '\n\n'.join(sections).strip()


def main():
    parser = argparse.ArgumentParser(
        description="Sync wiki/overview.md from wiki/index.md"
    )
    parser.add_argument("--write", action="store_true",
                        help="Overwrite wiki/overview.md")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if overview.md is out of sync")
    args = parser.parse_args()

    index_content = read_file(INDEX_FILE)
    if not index_content:
        print("Error: index.md not found")
        sys.exit(1)

    new_overview = build_overview(index_content)

    if args.write:
        from datetime import date
        new_overview = new_overview.replace("__TODAY__", date.today().isoformat())

        # Preserve manual sections not derived from index.md
        existing = read_file(OVERVIEW_FILE)
        if existing:
            new_slugs = get_current_overview_slugs(new_overview)
            manual = _extract_manual_sections(existing, new_slugs)
            if manual:
                new_overview = new_overview.rstrip() + '\n\n' + manual + '\n'

        OVERVIEW_FILE.write_text(new_overview, encoding="utf-8")
        print(f"✅ 已更新: {OVERVIEW_FILE.relative_to(REPO_ROOT)}")
        print(new_overview)
        return

    if args.check:
        current = read_file(OVERVIEW_FILE)
        new_with_date = new_overview.replace("__TODAY__", "__IGNORE_DATE__")

        # Reconstruct expected content including manual sections
        new_slugs = get_current_overview_slugs(new_with_date)
        manual = _extract_manual_sections(current, new_slugs)
        expected = new_with_date
        if manual:
            expected = expected.rstrip() + '\n\n' + manual + '\n'

        cur_stripped = re.sub(r'last_updated:.*', '', current)
        exp_stripped = re.sub(r'last_updated:.*', '', expected)

        if cur_stripped.strip() == exp_stripped.strip():
            print("✅ overview.md is in sync")
            sys.exit(0)
        else:
            print("❌ overview.md is out of sync")
            print()
            print("Current slugs in overview:",
                  get_current_overview_slugs(current))
            print("Expected slugs from index:",
                  get_current_overview_slugs(new_with_date))
            sys.exit(1)

    # Default: print to stdout
    print(new_overview)


if __name__ == "__main__":
    main()
