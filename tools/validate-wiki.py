#!/usr/bin/env python3
"""
Wiki validation — check integrity of all wiki pages.

Usage:
    python tools/validate-wiki.py               # report only
    python tools/validate-wiki.py --fix-stubs   # auto-create stub pages for phantom hubs
    python tools/validate-wiki.py --save        # save report to wiki/lint-report.md
    python tools/validate-wiki.py --json        # machine-readable JSON

Checks:
  1. Broken wikilinks — [[Target]] where Target.md doesn't exist
  2. Phantom hubs — broken links referenced by 2+ pages (eligible for stub)
  3. Index coverage — pages not listed in wiki/index.md
  4. Stub pages — files with only frontmatter
"""

import json
import re
import sys
from pathlib import Path

from _utils import read_file, extract_wikilinks, all_wiki_pages

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
STUB_THRESHOLD = 100  # body bytes below this = stub

META_PAGES = {"index.md", "log.md", "lint-report.md", "health-report.md"}


def all_wiki_pages():
    """Return set of all wiki page stems (lowercase), and dict of Path by stem."""
    stems = set()
    paths = {}
    for p in WIKI_DIR.rglob("*.md"):
        if p.name not in META_PAGES:
            stems.add(p.stem.lower())
            paths[p.stem.lower()] = p
    return stems, paths


def strip_frontmatter(content):
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].strip()
    return content.strip()


def validate():
    existing_stems, existing_paths = all_wiki_pages()
    index_content = read_file(INDEX_FILE).lower()

    broken_links = []  # [(source_page, target_link)]
    link_refcount = {}  # target_link → set of source pages

    # Scan all wiki pages for wikilinks
    for p in WIKI_DIR.rglob("*.md"):
        if p.name in META_PAGES:
            continue
        content = read_file(p)
        rel = str(p.relative_to(WIKI_DIR))
        for link in extract_wikilinks(content):
            link_stem = Path(link).stem.lower() if "/" in link else link.lower()
            if link_stem not in existing_stems:
                broken_links.append((rel, link))
                link_refcount.setdefault(link.lower(), set()).add(rel)

    # Unindexed pages
    unindexed = []
    for p in WIKI_DIR.rglob("*.md"):
        if p.name in META_PAGES or p.name == "overview.md":
            continue
        stem = p.stem.lower()
        if stem not in index_content:
            unindexed.append(str(p.relative_to(WIKI_DIR)))

    # Stub pages
    stubs = []
    for p in WIKI_DIR.rglob("*.md"):
        if p.name in META_PAGES:
            continue
        content = read_file(p)
        body = strip_frontmatter(content)
        if len(body) < STUB_THRESHOLD:
            stubs.append({
                "path": str(p.relative_to(WIKI_DIR)),
                "body_bytes": len(body),
            })

    # Phantom hubs — broken links referenced by 2+ pages
    phantom_hubs = {
        link: sorted(sources)
        for link, sources in link_refcount.items()
        if len(sources) >= 2
    }

    return {
        "broken_links": broken_links,
        "phantom_hubs": phantom_hubs,
        "unindexed": unindexed,
        "stubs": stubs,
    }


def auto_fix_stubs(phantom_hubs):
    """Create stub pages for phantom hubs."""
    created = []
    for link, sources in phantom_hubs.items():
        clean = link.strip("[]").strip()
        # Determine type: TitleCase entities → entity, lowercase → concept?
        if clean[0].isupper():
            page_type = "entity"
            subdir = "entities"
        else:
            page_type = "concept"
            subdir = "concepts"

        dest = WIKI_DIR / subdir / f"{clean}.md"
        if dest.exists():
            continue

        content = f"""---
title: "{clean}"
type: {page_type}
tags: []
sources: []
last_updated: 1970-01-01
---

Stub page — auto-created by validate-wiki.py.

Referenced by: {', '.join(sources)}
"""
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        created.append(str(dest.relative_to(REPO_ROOT)))

    return created


def format_report(data):
    lines = ["# Wiki Validation Report\n"]

    # Broken links
    bl = data["broken_links"]
    lines.append(f"## Broken Wikilinks ({len(bl)} found)")
    lines.append("")
    if bl:
        for src, target in bl[:20]:
            lines.append(f"- `wiki/{src}` → [[{target}]]")
        if len(bl) > 20:
            lines.append(f"  ... and {len(bl) - 20} more")
    else:
        lines.append("None found. ✅")
    lines.append("")

    # Phantom hubs
    ph = data["phantom_hubs"]
    lines.append(f"## Phantom Hubs ({len(ph)} eligible for stub creation)")
    lines.append("")
    if ph:
        for link, sources in sorted(ph.items()):
            lines.append(f"- [[{link}]] — {len(sources)} refs: {', '.join(sources)}")
    else:
        lines.append("None found. ✅")
    lines.append("")

    # Unindexed
    ui = data["unindexed"]
    lines.append(f"## Unindexed Pages ({len(ui)} not in index.md)")
    lines.append("")
    if ui:
        for p in ui[:20]:
            lines.append(f"- `wiki/{p}`")
        if len(ui) > 20:
            lines.append(f"  ... and {len(ui) - 20} more")
    else:
        lines.append("All pages indexed. ✅")
    lines.append("")

    # Stubs
    st = data["stubs"]
    lines.append(f"## Stub Pages ({len(st)} with <{STUB_THRESHOLD}B body)")
    lines.append("")
    if st:
        for s in st:
            lines.append(f"- `wiki/{s['path']}` — {s['body_bytes']}B body")
    else:
        lines.append("None found. ✅")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    fix_stubs = "--fix-stubs" in sys.argv
    save = "--save" in sys.argv
    json_output = "--json" in sys.argv

    data = validate()

    if fix_stubs:
        created = auto_fix_stubs(data["phantom_hubs"])
        if created:
            print(f"Created {len(created)} stub pages:")
            for p in created:
                print(f"  + {p}")
        else:
            print("No stub pages needed.")
        print()

        # Re-run validation after fix
        data = validate()

    if json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        report = format_report(data)
        print(report)
        if save:
            report_path = WIKI_DIR / "lint-report.md"
            report_path.write_text(report, encoding="utf-8")
            print(f"Saved to: {report_path.relative_to(REPO_ROOT)}")
