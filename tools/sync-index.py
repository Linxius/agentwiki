#!/usr/bin/env python3
"""
Auto-update wiki/index.md with missing page entries.

Scans wiki/concepts/, wiki/entities/, wiki/sources/ for .md files,
checks which ones are referenced in index.md via [Title](path) links,
and adds missing entries under the appropriate ## section.

Usage:
    python tools/sync-index.py              # dry-run: print what would change
    python tools/sync-index.py --write      # overwrite wiki/index.md
    python tools/sync-index.py --check      # exit 1 if out of sync
    python tools/sync-index.py --prune      # remove entries pointing to missing files

Designed to be called from health.py auto-fix.
"""

import re
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def scan_wiki_pages() -> dict[str, list[dict]]:
    """Scan wiki/concepts/, entities/, sources/ for .md files.
    
    Returns dict: category -> [(slug, title, path)]
    """
    categories = {
        "concepts": [],
        "entities": [],
        "sources": [],
    }
    
    for cat in categories:
        cat_dir = WIKI_DIR / cat
        if not cat_dir.exists():
            continue
        for md_file in sorted(cat_dir.glob("*.md")):
            slug = md_file.stem
            # Read title from frontmatter or first heading
            content = read_file(md_file)
            title = None
            
            # Try frontmatter title
            fm_match = re.search(r'^title:\s*"([^"]+)"', content, re.MULTILINE)
            if fm_match:
                title = fm_match.group(1)
            
            # Try first heading
            if not title:
                heading_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
                if heading_match:
                    title = heading_match.group(1).strip()
            
            # Fallback to slug
            if not title:
                title = slug.replace("-", " ").title()
            
            categories[cat].append({
                "slug": slug,
                "title": title,
                "path": f"{cat}/{md_file.name}",
                "file": md_file,
            })
    
    return categories


def parse_index_entries(content: str) -> dict[str, set[str]]:
    """Parse index.md sections and extract referenced slugs.
    
    Returns dict: section_name -> set of slugs
    """
    sections = {}
    current_section = None
    seen_slugs = set()
    
    for line in content.split("\n"):
        m = re.match(r'^## (.+)$', line.strip())
        if m:
            current_section = m.group(1).strip()
            seen_slugs = set()
            continue
        
        if current_section:
            # Match [Title](path/to/file.md) format
            for m in re.finditer(r'\[.*?\]\(([^\)]+)\)', line):
                path = m.group(1)
                slug = Path(path).stem
                seen_slugs.add(slug.lower())
        
        if current_section:
            sections.setdefault(current_section, seen_slugs)
    
    return sections


def map_category_to_section(category: str) -> str:
    """Map wiki/ subdirectory to index.md section header."""
    mapping = {
        "sources": "Sources",
        "entities": "Entities",
        "concepts": "Concepts",
    }
    return mapping.get(category, "Other")


def find_section_end(lines: list[str], start_idx: int) -> int:
    """Find the end of a section (next ## header or EOF)."""
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip().startswith("## "):
            return i
    return len(lines)


def find_section_start(lines: list[str], section_header: str) -> int:
    """Find the start line of a section."""
    for i, line in enumerate(lines):
        if line.strip() == f"## {section_header}":
            return i
    return -1


def build_missing_entries(category: str, pages: list[dict], existing_slugs: set[str]) -> list[dict]:
    """Build entries for pages not yet in index."""
    missing = []
    for page in pages:
        if page["slug"].lower() not in existing_slugs:
            missing.append(page)
    return missing


def format_entry(page: dict) -> str:
    """Format a single entry line for index.md.
    
    Uses [Title](path) format to match health.py's _parse_index_links.
    """
    slug = page["slug"]
    title = page["title"]
    cat = page["file"].parent.name  # concepts, entities, or sources
    return f"- [{title}]({cat}/{slug}.md)"


def prune_stale_entries(content: str) -> tuple[str, list[str]]:
    """Remove index.md lines whose link target file does not exist on disk.

    Handles both `(path.md)` and extension-less `(path)` links.
    Returns (new_content, removed_link_paths).
    """
    out_lines = []
    removed = []
    for line in content.split("\n"):
        m = re.match(r'^(\s*-\s*\[[^\]]+\]\()([^)]+)(\)\s*.*)$', line)
        if m:
            prefix, path, suffix = m.groups()
            target = WIKI_DIR / path
            if not target.exists() and not path.endswith(".md"):
                alt = WIKI_DIR / (path + ".md")
                if alt.exists():
                    target = alt
            if not target.exists():
                removed.append(path)
                continue
        out_lines.append(line)
    return "\n".join(out_lines), removed


def main():
    parser = argparse.ArgumentParser(
        description="Sync wiki/index.md with all wiki pages"
    )
    parser.add_argument("--write", action="store_true",
                        help="Overwrite wiki/index.md")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if out of sync")
    parser.add_argument("--prune", action="store_true",
                        help="Remove index entries pointing to missing files")
    args = parser.parse_args()
    
    if args.prune:
        content = read_file(INDEX_FILE)
        if not content:
            print("Error: index.md not found")
            sys.exit(1)
        new_content, removed = prune_stale_entries(content)
        if removed:
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"🗑️  Removed {len(removed)} stale entries: {', '.join(removed)}")
        else:
            print("✅ No stale entries to prune")
        return

    # Scan all wiki pages
    categories = scan_wiki_pages()
    total_pages = sum(len(v) for v in categories.values())
    
    # Read current index
    index_content = read_file(INDEX_FILE)
    if not index_content:
        print("Error: index.md not found")
        sys.exit(1)
    
    # Parse existing entries
    existing_entries = parse_index_entries(index_content)
    
    # Count missing per category
    missing_count = 0
    for cat, pages in categories.items():
        section_header = map_category_to_section(cat)
        existing_slugs = existing_entries.get(section_header, set())
        missing = build_missing_entries(cat, pages, existing_slugs)
        missing_count += len(missing)
    
    print(f"Scanned {total_pages} wiki pages across {len(categories)} categories")
    print(f"Missing from index: {missing_count}")
    
    if missing_count == 0:
        print("✅ index.md is in sync")
        return
    
    if args.check:
        print("❌ index.md is out of sync")
        sys.exit(1)
    
    # Generate update
    lines = index_content.split("\n")
    changes = []
    
    for cat, pages in categories.items():
        section_header = map_category_to_section(cat)
        existing_slugs = existing_entries.get(section_header, set())
        missing = build_missing_entries(cat, pages, existing_slugs)
        
        if not missing:
            continue
        
        section_start = find_section_start(lines, section_header)
        if section_start < 0:
            # Section doesn't exist - skip (or could create it)
            print(f"⚠️  Section '{section_header}' not found in index.md, skipping {len(missing)} entries")
            continue
        
        # Find end of section
        section_end = find_section_end(lines, section_start)
        
        # Insert missing entries at end of section (before next ## or EOF)
        new_entries = [format_entry(p) for p in missing]
        insertion = "\n" + "\n".join(new_entries) + "\n"
        lines.insert(section_end, insertion)
        changes.extend([(cat, p["slug"]) for p in missing])
    
    new_content = "\n".join(lines)
    
    print(f"\nChanges to make:")
    for cat, slug in changes:
        print(f"  + {cat}/{slug}.md")
    
    if not args.write:
        print("\nDry-run complete. Run with --write to apply changes.")
        return
    
    # Write update
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"\n✅ Updated {INDEX_FILE.relative_to(REPO_ROOT)}")
    print(f"   Added {len(changes)} entries")


if __name__ == "__main__":
    main()
