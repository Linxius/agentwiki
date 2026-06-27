#!/usr/bin/env python3
"""
inbox — process links in inbox.md + convert local files in inbox/ to markdown.

Usage:
    python tools/inbox.py                    # process links + convert local files
    python tools/inbox.py --list             # show links in inbox.md without processing
    python tools/inbox.py --list-local       # show local files in inbox/ without converting
    python tools/inbox.py --no-scan          # only process links, skip local files
    python tools/inbox.py --process-only     # only process, skip inbox.md cleanup

Supported links in inbox.md:
    - https://arxiv.org/abs/2401.12345       arXiv paper
    - https://example.com/article            web page
    - 2401.12345                              arXiv ID
    - https://github.com/user/repo.git       git repo → clone + code-read
    - git@github.com:user/repo.git           git repo (SSH) → clone + code-read
    - D:/Code/some-project                   local path → code-read
    - /home/user/project                     local path (unix) → code-read

Supported local files in inbox/:
    .pdf     → pdf2md.py (mineru/arxiv2md backend)
    .html    → trafilatura
    .docx/.pptx/.odt → pandoc (if installed)
    .txt/.rst/.text  → copy as markdown
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
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

GIT_URL_PATTERN = re.compile(
    r"^(https?://.*\.git"
    r"|git@[\w.-]+:.*\.git"
    r"|https?://github\.com/[\w.-]+/[\w.-]+"
    r"|https?://gitlab\.com/[\w.-]+/[\w.-]+"
    r"|https?://bitbucket\.org/[\w.-]+/[\w.-]+"
    r"|git@[\w.-]+:[\w.-]+/[\w.-]+)"
)


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
            url = url_match.group(1).rstrip('`).,')
            arxiv_id = extract_arxiv_id(url)
            if arxiv_id:
                items.append({"link": url, "type": "arxiv", "raw": line})
            elif is_git_url(url):
                items.append({"link": url, "type": "git", "raw": line})
            elif is_url(url):
                items.append({"link": url, "type": "url", "raw": line})
            continue

        # git SSH pattern
        git_match = re.match(r'^\s*[-*]\s*(git@[\w.-]+:\S+)', line)
        if git_match:
            url = git_match.group(1).rstrip('`).,')
            if is_git_url(url):
                items.append({"link": url, "type": "git", "raw": line})
                continue

        # arXiv ID pattern
        arx = extract_arxiv_id(line)
        if arx:
            items.append({"link": line, "type": "arxiv", "raw": line})
            continue

        # local path pattern
        path_match = re.match(r'^\s*[-*]\s*([\w]:[/\\]|/|\.\.?/)\S+', line)
        if path_match:
            raw_path = line.lstrip("-* ").strip()
            normalized = normalize_local_path(raw_path)
            if normalized:
                items.append({"link": str(normalized), "type": "local", "raw": line})

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


def is_git_url(text: str) -> bool:
    return bool(GIT_URL_PATTERN.match(text.strip()))


def normalize_local_path(text: str) -> Path | None:
    """Normalize a local path, converting MSYS/Git Bash /d/... to D:/... on Windows."""
    p = Path(text.strip())
    if p.exists() and (p.is_file() or p.is_dir()):
        return p
    # MSYS/Git Bash style: /d/Code/... -> D:/Code/...
    if os.name == "nt" and re.match(r"^/[a-zA-Z]/", text):
        converted = Path(text[1] + ":" + text[2:])
        if converted.exists() and (converted.is_file() or converted.is_dir()):
            return converted
    return None


def is_local_path(text: str) -> bool:
    return normalize_local_path(text) is not None


def process_code(item: dict, out_dir: Path) -> str | None:
    """Log a git/local item for agent subagent handling (no direct LLM call)."""
    link = item["link"]
    print(f"  [code] {link} — 待子代理处理")
    return None


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
        from arxiv2md import ingest_paper_sync
        result = ingest_paper_sync(arxiv_id)
        return result.content
    except ImportError:
        pass
    finally:
        # Clean up arxiv2md cache
        cache_dir = REPO_ROOT / ".arxiv2md_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)

    # Fallback: use pdf2md.py subprocess
    pdf2md_script = REPO_ROOT / "tools" / "pdf2md.py"
    if pdf2md_script.exists():
        fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix=f"arxiv_{arxiv_id}_")
        os.close(fd)
        tmp = Path(tmp_path)
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


# ─── Local file conversion ─────────────────────────────────────────

SLUGIFY_PATTERN = re.compile(r"[^\w\s-]")

def slugify(name: str) -> str:
    name = Path(name).stem
    name = SLUGIFY_PATTERN.sub("", name.lower())
    name = re.sub(r"[\s_]+", "-", name).strip("-")
    return name


def _convert_pdf(file_path: Path) -> Path | None:
    """Convert PDF via pdf2md.py subprocess. Return output path or None."""
    pdf2md = REPO_ROOT / "tools" / "pdf2md.py"
    if not pdf2md.exists():
        print("    SKIP (pdf2md.py not found)")
        return None

    result = subprocess.run(
        [sys.executable, str(pdf2md), str(file_path)],
        capture_output=True, text=True, timeout=300,
    )

    if result.returncode != 0:
        print(f"    FAIL: {result.stderr.strip()[-300:]}")
        return None

    # Parse stdout for → path
    for line in result.stdout.splitlines():
        m = re.search(r'→ ([\w/.\-]+\.md)', line)
        if m:
            out = (REPO_ROOT / m.group(1)).resolve()
            if out.exists():
                return out

    # Fallback: predictable path
    slug = slugify(file_path.stem)
    predicted = INBOX_DIR / slug / f"{slug}.md"
    return predicted if predicted.exists() else None


def _convert_html_file(file_path: Path, out_file: Path) -> bool:
    """Convert local HTML file to markdown."""
    try:
        html = file_path.read_text(encoding="utf-8")
    except Exception:
        try:
            html = file_path.read_text(encoding="latin-1")
        except Exception as e:
            print(f"    FAIL: {e}")
            return False

    md = clean_html(html)
    title = extract_title_from_html(html) or file_path.stem
    md = f"# {title}\n\n{md}"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(md, encoding="utf-8")
    return True


def _convert_via_pandoc(file_path: Path, out_file: Path) -> bool:
    """Convert DOCX/PPTX/ODT via pandoc."""
    if not shutil.which("pandoc"):
        print("    SKIP (pandoc not found)")
        return False

    result = subprocess.run(
        ["pandoc", str(file_path), "-t", "markdown", "-o", str(out_file)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"    FAIL: {result.stderr.strip()[-300:]}")
        return False
    return out_file.exists()


def _copy_text_file(file_path: Path, out_file: Path) -> bool:
    """Copy text file as markdown."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        try:
            content = file_path.read_text(encoding="latin-1")
        except Exception as e:
            print(f"    FAIL: {e}")
            return False

    if not content.startswith("# "):
        content = f"# {file_path.stem}\n\n{content}"

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(content, encoding="utf-8")
    return True


SKIP_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff", ".tif"}

def scan_and_convert_local_files() -> list[str]:
    """Scan inbox/ for non-markdown files and convert them in-place."""
    converted = []

    for file_path in sorted(INBOX_DIR.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.name == "inbox.md":
            continue
        if file_path.suffix.lower() == ".md":
            continue

        ext = file_path.suffix.lower()

        # Skip images and other binary assets silently
        if ext in SKIP_EXTS:
            continue

        rel = file_path.relative_to(REPO_ROOT)

        # Determine output dir: same parent if already in a dated dir
        parent = file_path.parent
        if re.match(r"^\d{4}-\d{2}-\d{2}$", parent.name):
            out_dir = parent
        else:
            out_dir = parent / date.today().isoformat()
            out_dir.mkdir(parents=True, exist_ok=True)

        slug = slugify(file_path.stem)
        out_file = out_dir / f"{slug}.md"

        # Skip if already converted (companion .md exists in same dir)
        if (file_path.parent / f"{file_path.stem}.md").exists():
            print(f"  [{ext[1:]}] {rel} -> skip (already converted)")
            file_path.unlink()
            continue

        print(f"  [{ext[1:]}] {rel}")

        try:
            ok = False
            if ext == ".pdf":
                out = _convert_pdf(file_path)
                if out and out.exists():
                    converted.append(str(out.relative_to(REPO_ROOT)))
                    print(f"    -> {out.relative_to(REPO_ROOT)}")
                    file_path.unlink()
                    continue
            elif ext in (".html", ".htm"):
                ok = _convert_html_file(file_path, out_file)
            elif ext in (".docx", ".doc", ".pptx", ".ppt", ".odt"):
                ok = _convert_via_pandoc(file_path, out_file)
            elif ext in (".txt", ".text", ".rst"):
                ok = _copy_text_file(file_path, out_file)
            else:
                print(f"    SKIP (unsupported: {ext})")
                continue

            if ok and out_file.exists():
                file_path.unlink()
                converted.append(str(out_file.relative_to(REPO_ROOT)))
                print(f"    -> {out_file.relative_to(REPO_ROOT)}")
            else:
                print(f"    FAILED")
        except Exception as e:
            print(f"    FAIL: {e}")

    return converted


# ─── Main ───────────────────────────────────────────────────────────

def process_link(item: dict, out_dir: Path) -> str:
    """Process a single link and save to out_dir. Return saved file path."""
    item_type = item["type"]
    link = item["link"]

    today = date.today()
    file_dir = out_dir / today.isoformat()
    file_dir.mkdir(parents=True, exist_ok=True)

    slug = generate_slug(link)

    if item_type in ("git", "local"):
        return process_code(item, out_dir)
    elif item_type == "arxiv":
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


def process_inbox(process_only: bool = False, no_scan: bool = False) -> list[str]:
    """Process inbox.md links + convert local files. Return list of saved file paths."""
    saved = []

    # ── Step 1: inbox.md links ──
    items = read_inbox_md()
    if items:
        print(f"Found {len(items)} link(s) in {INBOX_MD}")
        print("-" * 40)

        out_dir = INBOX_DIR
        for item in items:
            try:
                saved_file = process_link(item, out_dir)
                if saved_file is not None:
                    saved.append(str(saved_file.relative_to(REPO_ROOT)))
                    print(f"    -> {saved_file.relative_to(REPO_ROOT)}")
            except Exception as e:
                print(f"    FAILED: {e}")

        if not process_only:
            content = INBOX_MD.read_text(encoding="utf-8")
            content = re.sub(r'^\s*[-*]\s*https?://\S+\s*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'^\s*[-*]\s*git@[\w.-]+:\S+\s*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'^\s*[-*]\s*\d{4}\.\d{4,5}[^\n]*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'^\s*[-*]\s*([\w]:[/\\]|/|\.\.?/)\S+\s*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'\n{3,}', '\n\n', content)
            INBOX_MD.write_text(content, encoding="utf-8")
            print("-" * 40)
            print(f"Cleared {INBOX_MD}")
    else:
        print(f"No links found in {INBOX_MD}")

    # ── Step 2: local files ──
    if not no_scan:
        local = scan_and_convert_local_files()
        if local:
            print(f"\nConverted {len(local)} local file(s)")
        else:
            print(f"\nNo local files to convert")

    return saved


def main():
    parser = argparse.ArgumentParser(description="Process inbox.md links + convert local files in inbox/")
    parser.add_argument("--list", action="store_true", help="List links without processing")
    parser.add_argument("--list-local", action="store_true", help="List local files in inbox/ without converting")
    parser.add_argument("--process-only", action="store_true", help="Only process links, skip inbox.md cleanup")
    parser.add_argument("--no-scan", action="store_true", help="Skip local file scanning")
    args = parser.parse_args()

    if args.list:
        items = read_inbox_md()
        type_labels = {"arxiv": "arXiv", "url": "web", "git": "git", "local": "local"}
        for i, item in enumerate(items, 1):
            label = type_labels.get(item["type"], item["type"])
            print(f"{i}. [{label}] {item['link']}")
        return

    if args.list_local:
        found = []
        for f in sorted(INBOX_DIR.rglob("*")):
            if not f.is_file() or f.name == "inbox.md" or f.suffix.lower() == ".md":
                continue
            if f.suffix.lower() in SKIP_EXTS:
                continue
            found.append(f.relative_to(REPO_ROOT))
        if found:
            print(f"Local files in inbox/ ({len(found)}):")
            for f in found:
                print(f"  {f}")
        else:
            print("No local files found in inbox/")
        return

    process_inbox(process_only=args.process_only, no_scan=args.no_scan)


if __name__ == "__main__":
    main()
