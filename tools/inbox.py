#!/usr/bin/env python3
"""
inbox — add a list of links, auto-convert each to a markdown file in inbox/.

Usage:
    python tools/inbox.py                    # process all links in inbox.md
    python tools/inbox.py --list             # show links in inbox.md without processing
    python tools/inbox.py --process-only     # only process, skip inbox.md cleanup

Supported formats in inbox.md:
    - https://arxiv.org/abs/2401.12345       arXiv paper
    - https://example.com/article            web page
    - 2401.12345                              arXiv ID
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import date

import requests

REPO_ROOT = Path(__file__).parent.parent
INBOX_DIR = REPO_ROOT / "raw" / "inbox"
INBOX_MD = INBOX_DIR / "inbox.md"

ARXIV_PATTERNS = [
    re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"arxiv\.org/pdf/(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$"),
]


# ─── Inbox.md parsing ───────────────────────────────────────────────

def read_inbox_md() -> list[dict]:
    """Parse inbox.md, return list of {'link': url, 'type': 'url'|'arxiv', ...}."""
    if not INBOX_MD.exists():
        return []

    content = INBOX_MD.read_text(encoding="utf-8")
    items = []

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("<!--") or line.startswith("---"):
            continue

        # URL pattern
        url_match = re.match(r'^\s*[-*]\s*(https?://\S+)', line)
        if url_match:
            url = url_match.group(1).rstrip('`).')
            arxiv_id = extract_arxiv_id(url)
            if arxiv_id:
                items.append({"link": url, "type": "arxiv", "raw": line})
            elif is_url(url):
                items.append({"link": url, "type": "url", "raw": line})
            continue

        # arXiv ID pattern
        arx = extract_arxiv_id(line)
        if arx:
            items.append({"link": line, "type": "arxiv", "raw": line})

    return items


def extract_arxiv_id(text: str) -> str | None:
    """Extract arXiv ID from text."""
    for p in ARXIV_PATTERNS:
        m = p.search(text)
        if m:
            return m.group(1)
    return None


def is_url(text: str) -> bool:
    """Check if text looks like a URL (not arXiv)."""
    return text.startswith("http://") or text.startswith("https://")


# ─── Web page fetching ──────────────────────────────────────────────

def clean_html(html: str) -> str:
    """Extract readable text from HTML using trafilatura."""
    try:
        import trafilatura
        return trafilatura.extract(html, include_comments=False, include_tables=True) or ""
    except ImportError:
        pass

    # Fallback: basic tags only
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        return ""


def download_page(url: str) -> str:
    """Download a web page and return raw HTML."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or 'utf-8'
    return resp.text


def extract_title_from_html(html: str) -> str:
    """Extract title from HTML page."""
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        # Clean up title
        title = re.sub(r"\s+", " ", title)
        if title:
            return title
    return ""


def page_to_markdown(url: str) -> str:
    """Convert a web page URL to markdown."""
    try:
        html = download_page(url)
    except Exception as e:
        return f"# Error: Could not fetch {url}\n\n{e}"

    title = extract_title_from_html(html) or "Untitled"
    md = clean_html(html)
    md = f"# {title}\n\n" + md

    return md


# ─── arXiv conversion ───────────────────────────────────────────────

def fetch_arxiv(arxiv_id: str) -> str:
    """Use arxiv2md to convert an arXiv paper."""
    try:
        from arxiv2md import Arxiv2md
        converter = Arxiv2md(arxiv_id, output_format="markdown")
        return converter.convert()
    except ImportError:
        pass

    # Fallback: use pdf2md.py subprocess
    pdf2md_script = REPO_ROOT / "tools" / "pdf2md.py"
    if pdf2md_script.exists():
        tmp = Path(f"/tmp/arxiv_{arxiv_id}.md")
        try:
            result = subprocess.run(
                [sys.executable, str(pdf2md_script), arxiv_id, "-o", str(tmp)],
                capture_output=True, text=True, timeout=120,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding='utf-8'
            )
            if result.returncode == 0 and tmp.exists():
                return tmp.read_text(encoding="utf-8")
        except Exception:
            pass
        finally:
            if tmp.exists():
                tmp.unlink()

    return f"# arXiv: {arxiv_id}\n\n[arxiv2md not installed — try: pip install arxiv2markdown]\n\nOriginal: https://arxiv.org/abs/{arxiv_id}"


# ─── Slug generation ────────────────────────────────────────────────

def generate_slug(link: str) -> str:
    """Generate a filename-safe slug from a link."""
    h = hashlib.md5(link.encode()).hexdigest()[:8]

    # Try to get a descriptive part from the link
    if "arxiv.org" in link:
        arxid = extract_arxiv_id(link)
        if arxid:
            return f"arxiv-{arxid.replace('.', '')}-{h}"

    slug = link.replace("https://", "").replace("http://", "").replace("/", "-")
    slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff.-]', '', slug)
    slug = slug.strip(" -")

    if len(slug) > 80:
        slug = slug[:72] + f"-{h}"
    elif not slug:
        slug = f"page-{h}"

    return slug


# ─── Main ───────────────────────────────────────────────────────────

def process_link(item: dict, out_dir: Path) -> str:
    """Process a single link and save to out_dir. Return saved file path."""
    item_type = item["type"]
    link = item["link"]

    today = date.today()
    file_dir = out_dir / today.isoformat()
    file_dir.mkdir(parents=True, exist_ok=True)

    slug = generate_slug(link)

    if item_type == "arxiv":
        print(f"  [arXiv] {link}")
        content = fetch_arxiv(link)
        suffix = ".md"
    else:
        print(f"  [web] {link}")
        content = page_to_markdown(link)
        suffix = ".md"

    out_file = file_dir / f"{slug}{suffix}"
    out_file.write_text(content, encoding="utf-8")
    return out_file


def process_inbox(process_only: bool = False) -> list[str]:
    """Process all links in inbox.md. Return list of saved file paths."""
    items = read_inbox_md()

    if not items:
        print(f"No links found in {INBOX_MD}")
        print("")
        if not INBOX_MD.exists():
            print(f"Create {INBOX_MD} and add links like:")
            print("  - https://arxiv.org/abs/2401.12345")
            print("  - https://example.com/article")
        return []

    print(f"Found {len(items)} link(s) in {INBOX_MD}")
    print("-" * 40)

    out_dir = INBOX_DIR
    saved = []

    for item in items:
        try:
            saved_file = process_link(item, out_dir)
            saved.append(str(saved_file.relative_to(REPO_ROOT)))
            print(f"    -> {saved_file.relative_to(REPO_ROOT)}")
        except Exception as e:
            print(f"    FAILED: {e}")

    if not process_only:
        # Clear inbox.md links (keep header)
        content = INBOX_MD.read_text(encoding="utf-8")
        content = re.sub(r'^\s*[-*]\s*https?://\S+\s*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*[-*]\s*\d{4}\.\d{4,5}[^\n]*\n?', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n{3,}', '\n\n', content)
        INBOX_MD.write_text(content, encoding="utf-8")
        print("-" * 40)
        print(f"Cleared {INBOX_MD}")

    return saved


def main():
    parser = argparse.ArgumentParser(description="Process inbox.md links")
    parser.add_argument("--list", action="store_true", help="List links without processing")
    parser.add_argument("--process-only", action="store_true", help="Only process, skip inbox.md cleanup")
    args = parser.parse_args()

    if args.list:
        items = read_inbox_md()
        for i, item in enumerate(items, 1):
            print(f"{i}. [{item['type']}] {item['link']}")
        return

    process_inbox(process_only=args.process_only)


if __name__ == "__main__":
    main()
