#!/usr/bin/env python3
from __future__ import annotations

"""
Structural health checks for the LLM Wiki.

Unlike lint.py (which includes expensive LLM-powered semantic analysis),
health.py is purely deterministic — zero API calls, fast enough to run
every session.

Usage:
    python tools/health.py              # print report to stdout
    python tools/health.py --save       # also save to wiki/health-report.md
    python tools/health.py --json       # machine-readable output

Checks:
  - Empty / stub files (pages with no real content beyond frontmatter)
  - Index sync (wiki/index.md entries vs actual files on disk)
  - Log coverage (source pages without a corresponding log entry)
  - Overview sync (wiki/overview.md vs wiki/index.md — auto-fixed)

Design boundary (see AGENTS.md):
  health.py = structural integrity, deterministic, run every session
  lint.py   = content quality, semantic (LLM), run every 10-15 ingests
"""

import re
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import date

from _utils import read_file

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
OVERVIEW_FILE = WIKI_DIR / "overview.md"

# Minimum content length (excluding frontmatter) to not be considered a stub
STUB_THRESHOLD_CHARS = 100


def all_wiki_pages() -> list[Path]:
    """All .md files in wiki/, excluding meta files."""
    exclude = {"index.md", "log.md", "lint-report.md", "health-report.md"}
    return [p for p in WIKI_DIR.rglob("*.md") if p.name not in exclude]


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3:].strip()
    return content.strip()


# ── Check: Empty / Stub files ───────────────────────────────────────

def check_empty_files(pages: list[Path], threshold: int = STUB_THRESHOLD_CHARS) -> list[dict]:
    """Find wiki pages that are empty or contain only frontmatter / minimal content."""
    results = []
    for p in pages:
        raw = read_file(p)
        body = strip_frontmatter(raw)
        if len(body) < threshold:
            results.append({
                "path": str(p.relative_to(REPO_ROOT)),
                "total_bytes": len(raw),
                "body_bytes": len(body),
                "status": "empty" if len(body) == 0 else "stub",
            })
    results.sort(key=lambda x: x["body_bytes"])
    return results


# ── Check: Index sync ───────────────────────────────────────────────

def _resolve_index_link(link: str) -> Path | None:
    """Resolve an index.md link to a disk path, auto-appending .md if needed."""
    p = WIKI_DIR / link
    if p.exists():
        return p.resolve()
    if not link.endswith(".md"):
        alt = WIKI_DIR / (link + ".md")
        if alt.exists():
            return alt.resolve()
    return None


def _parse_index_links(index_content: str) -> set[str]:
    """Extract markdown link targets from index.md.

    Matches patterns like: [Title](sources/slug.md) or [Title](sources/slug)
    Returns set of relative paths (e.g. 'sources/slug.md' or 'sources/slug').
    """
    return set(re.findall(r'\[.*?\]\(([^)]+)\)', index_content))


def check_index_sync(pages: list[Path]) -> dict:
    """Compare wiki/index.md entries against actual files on disk.

    Returns:
        {
            "in_index_not_on_disk": [...],   # stale index entries
            "on_disk_not_in_index": [...],   # missing from index
        }
    """
    index_content = read_file(INDEX_FILE)
    index_links = _parse_index_links(index_content)

    # Normalize index links to absolute paths for comparison
    # overview.md is listed under ## Overview, not in the per-type sections.
    # Exclude it from both sides to avoid false positives.
    meta_pages = {"overview.md"}

    stale_links = []
    index_paths = set()
    for link in index_links:
        if Path(link).name in meta_pages:
            continue
        resolved = _resolve_index_link(link)
        if resolved is None:
            stale_links.append(link)
        else:
            index_paths.add(resolved)

    disk_paths = set()
    for p in pages:
        if p.name not in meta_pages:
            disk_paths.add(p.resolve())

    in_index_not_on_disk = sorted(stale_links)
    on_disk_not_in_index = [
        str(p.relative_to(REPO_ROOT)) for p in sorted(disk_paths - index_paths)
    ]

    return {
        "in_index_not_on_disk": in_index_not_on_disk,
        "on_disk_not_in_index": on_disk_not_in_index,
    }


# ── Check: Log coverage ────────────────────────────────────────────

def _parse_log_entries(log_content: str) -> list[str]:
    """Extract page titles/slugs from log.md entries.

    Log format: ## [YYYY-MM-DD] ingest | Title Here
    Returns list of cleaned lowercase title strings.

    Cleaning: strip brackets and URLs from wikilink format
    e.g. '[Title](path) — note' -> 'title'
    """
    titles = []
    for m in re.finditer(r'^## \[\d{4}-\d{2}-\d{2}\] ingest \| (.+)$', log_content, re.MULTILINE):
        raw = m.group(1).strip()
        # Strip wikilink format: '[Title](link) — note' -> 'Title'
        cleaned = re.sub(r'^\[(.+?)\]\([^)]*\).*', r'\1', raw)
        titles.append(cleaned.lower())
    return titles


def check_log_coverage(pages: list[Path]) -> list[dict]:
    """Find source pages that have no corresponding ingest entry in log.md.

    Only checks wiki/sources/*.md — entity/concept pages are created as
    side-effects of ingest and don't need their own log entry.

    Matching strategy (in order):
    1. Exact match: slug or frontmatter title exactly equals a log entry
    2. Substring match: frontmatter title is contained in a log entry (or vice versa)
    3. Slug match: log entry slug (from URL path) matches the page slug
    """
    log_content = read_file(LOG_FILE)
    logged_titles = _parse_log_entries(log_content)

    source_dir = WIKI_DIR / "sources"
    if not source_dir.exists():
        return []

    missing = []
    for p in sorted(source_dir.glob("*.md")):
        slug = p.stem.lower().replace("-", " ").replace("_", " ")

        content = read_file(p)
        title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        fm_title = title_match.group(1).strip().lower() if title_match else ""

        matched = False

        # Strategy 1: Exact match
        if slug in logged_titles or fm_title in logged_titles:
            matched = True

        # Strategy 2: Substring match (handles truncated log titles)
        if not matched:
            for lt in logged_titles:
                if fm_title and len(fm_title) > 20:
                    if fm_title in lt or lt in fm_title:
                        matched = True
                        break
                # Also check if log title slug (from URL) matches
                if not matched:
                    log_slug_match = re.search(r'\[.*?\]\((sources/[\w-]+\.md)\)', lt)
                    if log_slug_match:
                        log_slug = log_slug_match.group(1).lower()
                        if slug.replace(" ", "-") in log_slug or log_slug in slug.replace(" ", "-"):
                            matched = True
                            break

        if not matched:
            missing.append({
                "path": str(p.relative_to(REPO_ROOT)),
                "slug": p.stem,
                "title": fm_title or p.stem,
            })

    return missing


# ── Check: Overview sync ──────────────────────────────────────────

SYNC_SCRIPT = REPO_ROOT / "tools" / "sync-overview.py"
SYNC_INDEX_SCRIPT = REPO_ROOT / "tools" / "sync-index.py"
ISSUES_FILE = WIKI_DIR / "issues.md"


def check_overview_sync() -> dict:
    """Check if overview.md is in sync with index.md. Auto-fixes if out of sync.

    Returns:
        {"status": "synced"|"fixed"|"skipped", "reason": "..."}
    """
    if not SYNC_SCRIPT.exists():
        return {"status": "skipped", "reason": "sync-overview.py not found"}

    ENCODING_ARGS = dict(encoding='utf-8', errors='replace')

    # Check first
    check = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--check"],
        capture_output=True, text=True, timeout=30, **ENCODING_ARGS,
    )

    if check.returncode == 0:
        return {"status": "synced", "reason": ""}

    # Auto-fix
    fix = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--write"],
        capture_output=True, text=True, timeout=30, **ENCODING_ARGS,
    )

    if fix.returncode == 0:
        return {"status": "fixed", "reason": (fix.stdout or "").strip()}
    else:
        return {"status": "skipped", "reason": f"auto-fix failed: {(fix.stderr or '').strip()}"}


# ── Fix: Index sync ─────────────────────────────────────────────────

def fix_index_sync(fix_stale: bool = False) -> dict:
    """Auto-fix index sync issues.

    Always: add missing entries via sync-index.py --write (low risk incremental).
    Only when fix_stale: prune stale entries via sync-index.py --prune.

    Returns:
        {"add": "success"|"skipped", "prune": "success"|"skipped"}
    """
    result = {"add": "skipped", "prune": "skipped"}

    # Always auto-fix missing entries (incremental, low risk)
    check = subprocess.run(
        [sys.executable, str(SYNC_INDEX_SCRIPT), "--check"],
        capture_output=True, text=True, timeout=30,
        encoding='utf-8', errors='replace',
    )
    if check.returncode != 0:
        write = subprocess.run(
            [sys.executable, str(SYNC_INDEX_SCRIPT), "--write"],
            capture_output=True, text=True, timeout=30,
            encoding='utf-8', errors='replace',
        )
        if write.returncode == 0:
            match = re.search(r'Added (\d+) entries', write.stdout)
            count = int(match.group(1)) if match else 0
            result["add"] = "success"
            result["_added_count"] = count

    # Only prune stale entries when explicitly requested (destructive)
    if fix_stale:
        prune = subprocess.run(
            [sys.executable, str(SYNC_INDEX_SCRIPT), "--prune"],
            capture_output=True, text=True, timeout=30,
            encoding='utf-8', errors='replace',
        )
        if prune.returncode == 0:
            match = re.search(r'Removed (\d+) stale entries', prune.stdout)
            if match:
                result["prune"] = "success"
                result["_pruned_count"] = int(match.group(1))
            else:
                result["prune"] = "success"  # "No stale entries" also success
        else:
            result["prune"] = f"failed: {(prune.stderr or '').strip()}"

    return result


# ── Fix: Stub pages ─────────────────────────────────────────────────

def fix_stubs(stubs: list[dict]) -> list[str]:
    """Register stub pages to wiki/issues.md under ## Stub Pages.

    Idempotent: skips paths already in the issues file.
    Does NOT generate content (stub filling is a lint.py/LLM task).

    Returns:
        List of registered paths.
    """
    issues_content = read_file(ISSUES_FILE)

    # Check if stubs already registered (idempotent guard)
    registered = []
    for stub in stubs:
        if stub["path"] in issues_content:
            continue
        path = stub["path"]
        status = stub["status"]
        body = stub["body_bytes"]
        registered.append(stub)
        issues_content += f"- `{path}` — {status}, {body} bytes\n"

    if registered:
        issues_content += "\n"  # trailing newline
        ISSUES_FILE.write_text(issues_content, encoding="utf-8")

    return registered


# ── Report Generation ───────────────────────────────────────────────

def run_health(fix: bool = False) -> dict:
    """Run all health checks, return structured results.

    Default behavior (no --fix):
      - Auto-fix: index missing entries (incremental add), overview sync
    With --fix:
      - Plus: index stale entries (prune), stub pages registration to issues.md

    Args:
        fix: Enable all auto-fixes including destructive operations (prune, register).

    Returns:
        Structured results dict.
    """
    pages = all_wiki_pages()
    fixed = {}

    # Default auto-fix: index missing entries (low risk incremental add)
    fix_res = fix_index_sync(fix_stale=fix)
    fixed["index_missing_added"] = fix_res.get("add") == "success"
    fixed["index_stale_pruned"] = fix_res.get("prune") == "success" and fix
    fixed["_added_count"] = fix_res.get("_added_count", 0)
    fixed["_pruned_count"] = fix_res.get("_pruned_count", 0)

    # Run checks after fixes (reflect post-fix state)
    index_sync = check_index_sync(pages)
    empty_files = check_empty_files(pages)
    log_coverage = check_log_coverage(pages)
    overview_sync = check_overview_sync()

    # Only --fix: register stubs to issues.md (idempotent, no content generation)
    stubs_registered = 0
    if fix and empty_files:
        stubs_registered = len(fix_stubs(empty_files))

    return {
        "date": date.today().isoformat(),
        "total_pages": len(pages),
        "empty_files": empty_files,
        "index_sync": index_sync,
        "log_coverage": log_coverage,
        "overview_sync": overview_sync,
        "fixed": fixed,
        "_stubs_registered": stubs_registered,
    }


def format_report(results: dict) -> str:
    """Format health check results as markdown."""
    lines = [
        f"# Wiki Health Report — {results['date']}",
        "",
        f"Scanned {results['total_pages']} wiki pages. "
        "Checks are purely structural (no LLM calls).",
        "",
    ]

    # ── Empty / Stub Files
    empty = results["empty_files"]
    lines.append(f"## Empty / Stub Files ({len(empty)} found)")
    lines.append("")
    if empty:
        lines.append("| Page | Total Bytes | Body Bytes | Status |")
        lines.append("|---|---|---|---|")
        for ef in empty:
            emoji = "🔴" if ef["status"] == "empty" else "🟡"
            lines.append(f"| `{ef['path']}` | {ef['total_bytes']} | {ef['body_bytes']} | {emoji} {ef['status']} |")
    else:
        lines.append("All pages have content beyond frontmatter. ✅")
    lines.append("")

    # ── Index Sync
    isync = results["index_sync"]
    stale = isync["in_index_not_on_disk"]
    missing = isync["on_disk_not_in_index"]
    total_issues = len(stale) + len(missing)
    lines.append(f"## Index Sync ({total_issues} issues)")
    lines.append("")

    if stale:
        lines.append("### Stale Index Entries (in index.md but no file on disk)")
        for s in stale:
            lines.append(f"- `{s}`")
        lines.append("")

    if missing:
        lines.append("### Missing from Index (file exists but not in index.md)")
        for m in missing:
            lines.append(f"- `{m}`")
        lines.append("")

    if not stale and not missing:
        lines.append("index.md is in sync with disk. ✅")
        lines.append("")

    # ── Overview Sync
    ov = results["overview_sync"]
    lines.append(f"## Overview Sync")
    lines.append("")
    if ov["status"] == "synced":
        lines.append("overview.md is in sync with index.md. ✅")
    elif ov["status"] == "fixed":
        lines.append(f"🛠️  overview.md 已自动修复（与 index.md 不同步）")
        for rl in ov["reason"].split("\n"):
            lines.append(f"  > {rl}")
    else:
        lines.append(f"⏭️  {ov['reason']}")
    lines.append("")

    # ── Log Coverage
    log_missing = results["log_coverage"]
    lines.append(f"## Log Coverage ({len(log_missing)} source pages without log entry)")
    lines.append("")
    if log_missing:
        lines.append("These source pages have no corresponding `ingest` entry in log.md:")
        lines.append("")
        for lm in log_missing:
            lines.append(f"- `{lm['path']}` — {lm['title']}")
    else:
        lines.append("All source pages have corresponding log entries. ✅")
    lines.append("")

    # ── Auto-fixed ────────────────────────────────────────────────
    fixed = results.get("fixed", {})
    stubs_reg = results.get("_stubs_registered", 0)
    added = fixed.get("_added_count", 0)
    pruned = fixed.get("_pruned_count", 0)
    auto_fixes = []
    if added:
        auto_fixes.append(f"index.md: added {added} missing entries")
    if pruned:
        auto_fixes.append(f"index.md: pruned {pruned} stale entries")
    if stubs_reg:
        auto_fixes.append(f"issues.md: registered {stubs_reg} stub pages")
    if auto_fixes:
        lines.append("## Auto-fixed")
        lines.append("")
        for af in auto_fixes:
            lines.append(f"- {af}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Structural health checks for the LLM Wiki (deterministic, no LLM calls)"
    )
    parser.add_argument("--save", action="store_true",
                        help="Save report to wiki/health-report.md")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON instead of markdown")
    parser.add_argument("--fix", action="store_true",
                        help="Run all auto-fixes including stale pruning and stub registration (default always fixes: index missing entries + overview sync)")
    args = parser.parse_args()

    results = run_health(fix=args.fix)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        report = format_report(results)
        print(report)

        if args.save:
            report_path = WIKI_DIR / "health-report.md"
            report_path.write_text(report, encoding="utf-8")
            print(f"\nSaved: {report_path.relative_to(REPO_ROOT)}")
