#!/usr/bin/env python3
"""
inbox — process links in inbox.md + convert local files in inbox/ to markdown.

Usage:
    python tools/inbox.py                    # process links + convert local files
    python tools/inbox.py --list             # show links in inbox.md without processing
    python tools/inbox.py --list-local       # show local files in inbox/ without converting
    python tools/inbox.py --dedup            # deduplicate by arxiv ID and rewrite inbox.md
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
    re.compile(r"arxiv\.org/html/(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"alphaxiv\.org/abs/(\d{4}\.\d{4,5})"),
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
    """Parse inbox.md, return list of {'link': url, 'type': 'url'|'arxiv', ...}.

    Deduplicates by arxiv ID: multiple URLs for the same paper (abs/pdf/GitHub/project page)
    are merged into one entry with related_urls.
    """
    if not INBOX_MD.exists():
        return []

    content = INBOX_MD.read_text(encoding="utf-8")
    raw_items = []

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--") or stripped.startswith("---"):
            continue

        # Related/sub-item line: parse URLs and attach to preceding item
        if is_related_line(line):
            if raw_items:
                last = raw_items[-1]
                related = last.setdefault("related_urls", [])
                # Extract all [text](url) pairs from the line
                for m in re.finditer(r'\[([^\]]+)\]\((https?://[^)]+)\)', line):
                    label = m.group(1).lower()
                    rurl = m.group(2).rstrip('`).,')
                    # Normalize: if it's an alphaXiv URL, convert to arxiv
                    rid = extract_arxiv_id(rurl)
                    rurl = normalize_url(rurl, rid)
                    rtype = _classify_url(rurl)
                    # Deduplicate: skip if same URL already in related
                    if not any(r["url"] == rurl for r in related):
                        related.append({"url": rurl, "label": label, "type": rtype})
            continue

        # Try markdown link format: - [text](url)
        md_match = re.match(r'^\s*[-*]\s*\[.+?\]\((https?://[^)]+)\)', line)
        if md_match:
            url = md_match.group(1).rstrip('`).,')
            arxiv_id = extract_arxiv_id(url)
            url = normalize_url(url, arxiv_id)
            item = {"link": url, "raw": line}
            if arxiv_id:
                item.update({"type": "arxiv", "arxiv_id": arxiv_id})
            elif is_git_url(url):
                item["type"] = "git"
            elif is_url(url):
                item["type"] = "url"
            else:
                continue
            raw_items.append(item)
            continue

        # Bare URL pattern: - https://...
        url_match = re.match(r'^\s*[-*]\s*(https?://\S+)', line)
        if url_match:
            url = url_match.group(1).rstrip('`).,')
            arxiv_id = extract_arxiv_id(url)
            url = normalize_url(url, arxiv_id)
            item = {"link": url, "raw": line}
            if arxiv_id:
                item.update({"type": "arxiv", "arxiv_id": arxiv_id})
            elif is_git_url(url):
                item["type"] = "git"
            elif is_url(url):
                item["type"] = "url"
            else:
                continue
            raw_items.append(item)
            continue

        # git SSH pattern
        git_match = re.match(r'^\s*[-*]\s*(git@[\w.-]+:\S+)', line)
        if git_match:
            url = git_match.group(1).rstrip('`).,')
            if is_git_url(url):
                raw_items.append({"link": url, "type": "git", "raw": line})
                continue

        # arXiv ID pattern
        arx = extract_arxiv_id(line)
        if arx:
            raw_items.append({"link": line, "type": "arxiv", "arxiv_id": arx, "raw": line})
            continue

        # local path pattern
        path_match = re.match(r'^\s*[-*]\s*([\w]:[/\\]|/|\.\.?/)\S+', line)
        if path_match:
            raw_path = line.lstrip("-* ").strip()
            normalized = normalize_local_path(raw_path)
            if normalized:
                raw_items.append({"link": str(normalized), "type": "local", "raw": line})

    # ── Deduplicate by arxiv ID ──
    # Group all arxiv-related URLs by paper ID.
    # Non-arxiv URLs (GitHub, project page) within 3 positions of an arxiv entry
    # are treated as related if no other arxiv entry is closer.
    items = _dedup_by_arxiv_id(raw_items)
    return items


def _dedup_by_arxiv_id(raw_items: list[dict]) -> list[dict]:
    """Group arxiv-related URLs by paper ID, associate nearby/related GitHub/project links.

    Two-pass matching:
      1. Position proximity (±5) + arxiv ID in text
      2. Title keyword matching for distant but clearly related links
    """
    if not raw_items:
        return []

    # Collect all arxiv IDs and their positions
    arxiv_positions = {}  # arxiv_id → list of indices
    for i, item in enumerate(raw_items):
        aid = item.get("arxiv_id")
        if aid:
            arxiv_positions.setdefault(aid, []).append(i)

    if not arxiv_positions:
        return raw_items

    # Build paper titles from arxiv entries (for keyword matching)
    paper_titles = {}  # arxiv_id → title text
    for arxiv_id, positions in arxiv_positions.items():
        for idx in positions:
            raw = raw_items[idx].get("raw", "")
            # Extract title from markdown link: [title](url) or just the text
            title_match = re.search(r'\[(.+?)\]\(', raw)
            if title_match:
                paper_titles[arxiv_id] = title_match.group(1)
                break
            else:
                paper_titles[arxiv_id] = raw

    seen_indices = set()
    result = []

    for arxiv_id, positions in arxiv_positions.items():
        group = [raw_items[i] for i in positions]

        # Prefer abs link as primary
        primary = None
        for item in group:
            if "/abs/" in item["link"]:
                primary = item
                break
        if not primary:
            primary = group[0]

        # Preserve any related_urls already parsed from indented related: lines
        existing_related = {r["url"] for r in primary.get("related_urls", [])}
        related_urls = list(primary.get("related_urls", []))
        for item in group:
            if item is not primary:
                url = item["link"]
                if url not in existing_related:
                    related_urls.append({"url": url, "type": _classify_url(url)})
                    existing_related.add(url)

        primary_idx = raw_items.index(primary)
        title = paper_titles.get(arxiv_id, "")

        # Pass 1: position proximity (±5) + arxiv ID match
        for offset in range(-5, 6):
            idx = primary_idx + offset
            if idx < 0 or idx >= len(raw_items) or idx in seen_indices:
                continue
            neighbor = raw_items[idx]
            if neighbor.get("arxiv_id") == arxiv_id:
                continue
            if neighbor["type"] in ("git", "url") and not neighbor.get("arxiv_id"):
                raw_text = neighbor.get("raw", "").lower()
                nurl = neighbor["link"]
                # Skip if already in related_urls (from parsed related: lines)
                if nurl in existing_related:
                    seen_indices.add(idx)
                    continue
                # Match by arxiv ID in text
                if arxiv_id.replace(".", "") in raw_text.replace(".", ""):
                    related_urls.append({"url": nurl, "type": _classify_url(nurl)})
                    seen_indices.add(idx)
                    continue
                # Match by title keywords in repo name or bookmark text
                if title and _title_matches_text(title, neighbor.get("raw", "")):
                    related_urls.append({"url": nurl, "type": _classify_url(nurl)})
                    seen_indices.add(idx)

        # Mark group indices as seen
        for pos in positions:
            seen_indices.add(pos)

        entry = dict(primary)
        entry["related_urls"] = related_urls
        entry["arxiv_id"] = arxiv_id
        result.append(entry)

    # Pass 2: unmatched GitHub/project URLs — try matching by title to nearest arxiv paper
    for i, item in enumerate(raw_items):
        if i in seen_indices:
            continue
        if item["type"] not in ("git", "url") or item.get("arxiv_id"):
            continue
        # Find best matching arxiv paper by title keywords
        best_match = _find_best_arxiv_match(item, raw_items, arxiv_positions, paper_titles, seen_indices)
        if best_match:
            # Add to that paper's related_urls
            for entry in result:
                if entry.get("arxiv_id") == best_match:
                    entry["related_urls"].append({"url": item["link"], "type": _classify_url(item["link"])})
                    seen_indices.add(i)
                    break

    # Add remaining non-arxiv, non-seen items
    for i, item in enumerate(raw_items):
        if i not in seen_indices:
            result.append(item)

    return result


# Common words to ignore when matching titles
_STOP_WORDS = frozenset({
    "a", "an", "the", "for", "of", "and", "or", "in", "on", "with", "to",
    "from", "by", "as", "at", "is", "are", "was", "were", "be", "been",
    "using", "via", "through", "towards", "based", "learn",
})

# Generic CS/3DGS terms that appear in many papers — not useful for disambiguation
_GENERIC_WORDS = frozenset({
    "gaussian", "splatting", "3d", "2d", "neural", "rendering", "reconstruction",
    "mesh", "surface", "quality", "efficient", "high", "real", "time", "realtime",
    "deep", "learning", "network", "model", "method", "approach", "framework",
    "view", "image", "radiance", "field", "volume", "volumetric", "graphics",
    "scene", "object", "objects", "view", "views", "novel", "synthesis", "generation",
    "representation", "geometry", "texture", "material", "lighting", "relighting",
    "inverse", "differentiable", "optimization", "training", "pipeline", "system",
})


def _extract_keywords(text: str, distinctive_only: bool = False) -> set[str]:
    """Extract significant keywords from a title/text.

    Preserves hyphenated terms (Ref-DGS, 3DGS, NeRF) as single tokens.
    Handles markdown link format [text](url) by extracting the link text.
    """
    # Extract link text from markdown links: [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\|.*$', '', text)
    text = re.sub(r'https?://\S+', '', text)
    words = set()
    # Split on whitespace and common separators, but NOT hyphens
    for w in re.split(r'[\s/:_.,:;!?()\'"]+', text):
        w = w.lower().strip().strip('-')
        if len(w) >= 3 and w not in _STOP_WORDS:
            words.add(w)
    if distinctive_only:
        words -= _GENERIC_WORDS
    return words


def _title_matches_text(paper_title: str, text: str) -> bool:
    """Check if a paper title has keyword overlap with a bookmark text/repo name.

    Uses distinctive keywords (filtering generic CS terms) to avoid false positives.
    Requires 2+ matching keywords, OR 1 compound term that looks like a paper-specific
    abbreviation (e.g. ref-dgs, 3dgs, nerf).
    """
    title_kw = _extract_keywords(paper_title, distinctive_only=True)
    text_kw = _extract_keywords(text, distinctive_only=True)
    if not title_kw or not text_kw:
        return False
    matches = title_kw & text_kw
    if len(matches) >= 2:
        return True
    # Single match: only accept if it's a short compound abbreviation (4-8 chars with hyphen)
    # e.g. "ref-dgs", "3dgs", "nerf" — NOT "high-fidelity", "surfaces"
    if len(matches) == 1:
        w = next(iter(matches))
        return "-" in w and 4 <= len(w) <= 8
    return False


def _find_best_arxiv_match(item: dict, raw_items: list[dict],
                           arxiv_positions: dict, paper_titles: dict,
                           seen_indices: set) -> str | None:
    """Find the best arxiv paper match for an unmatched GitHub/project URL.

    Uses distinctive keywords only (filters generic CS/3DGS terms) to avoid
    false positives between different papers in the same field.
    """
    item_text = item.get("raw", "")
    item_kw = _extract_keywords(item_text, distinctive_only=True)
    if not item_kw:
        return None

    best_id = None
    best_score = 0

    for arxiv_id, positions in arxiv_positions.items():
        title = paper_titles.get(arxiv_id, "")
        title_kw = _extract_keywords(title, distinctive_only=True)
        if not title_kw:
            continue
        overlap = title_kw & item_kw
        score = len(overlap)
        if score > best_score:
            best_score = score
            best_id = arxiv_id

    # Require 2+ keywords, or 1 short compound abbreviation (4-8 chars with hyphen)
    if best_score >= 2:
        return best_id
    if best_score == 1 and best_id:
        title_kw = _extract_keywords(paper_titles.get(best_id, ""), distinctive_only=True)
        item_kw_check = _extract_keywords(item_text, distinctive_only=True)
        overlap = title_kw & item_kw_check
        if any("-" in w and 4 <= len(w) <= 8 for w in overlap):
            return best_id
    return None


def _classify_url(url: str) -> str:
    """Classify a URL into a human-readable type label."""
    if "github.com" in url or "gitlab.com" in url:
        return "code"
    if "arxiv.org" in url or "alphaxiv.org" in url:
        if "/pdf/" in url:
            return "pdf"
        return "abs"
    if any(kw in url.lower() for kw in ["project", "page", "homepage", ".io", ".dev"]):
        return "project"
    return "web"


def extract_arxiv_id(text: str) -> str | None:
    """Extract arXiv ID from text."""
    for p in ARXIV_PATTERNS:
        m = p.search(text)
        if m:
            return m.group(1)
    return None


def normalize_url(url: str, arxiv_id: str | None = None) -> str:
    """Normalize URL: alphaxiv.org → arxiv.org, arxiv.org/html/ → arxiv.org/abs/, strip UTM/cursor params.

    Args:
        url: The original URL string.
        arxiv_id: If provided and URL matches a known arxiv variant, reconstruct a clean arxiv.org/abs/ URL.
    """
    # Strip UTM and other tracking query params
    url = re.sub(r'\?utm_[^&\s]+(&|$)', r'\1', url)
    url = re.sub(r'\?chatId=[^&\s]+(&|$)', r'\1', url)
    url = url.rstrip('?&')

    # alphaxiv.org/abs/ID → arxiv.org/abs/ID
    if arxiv_id and "alphaxiv.org" in url:
        return f"https://arxiv.org/abs/{arxiv_id}"

    # arxiv.org/html/ID → arxiv.org/abs/ID (HTML 全文版与 abs 页等效)
    if arxiv_id and "arxiv.org/html/" in url:
        return f"https://arxiv.org/abs/{arxiv_id}"

    return url


def is_related_line(line: str) -> bool:
    """Check if line is a sub-item/related URL line (indented with '  - related:' or similar)."""
    return bool(re.match(r'^\s{2,}[-*]\s+(related|see also|notes):', line, re.IGNORECASE))


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

def fetch_arxiv(arxiv_id: str, out_path: Path | None = None) -> str:
    """Use arxiv2md (Linxius) to convert an arXiv paper.

    If out_path is given, writes output there (CLI mode, handles figures).
    Otherwise returns content string (Python API mode, no figures).
    """
    if out_path:
        # CLI mode: Linxius version outputs to a directory
        out_dir = out_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "arxiv2md", arxiv_id,
                 "--frontmatter", "--remove-toc",
                 "-o", str(out_dir)],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                # Linxius outputs to <dir>/<paper-title>.md — find it
                md_files = list(out_dir.glob("*.md"))
                if md_files:
                    generated = md_files[0]
                    content = generated.read_text(encoding="utf-8")
                    # Rename to our expected filename
                    if generated != out_path:
                        generated.rename(out_path)
                    return content
        except Exception:
            pass
        # Fallback to Python API if CLI fails
        return _fetch_arxiv_api(arxiv_id)

    return _fetch_arxiv_api(arxiv_id)


def _fetch_arxiv_api(arxiv_id: str) -> str:
    """Fallback: use arxiv2md Python API (no figure handling)."""
    try:
        from arxiv2md import ingest_paper_sync
        result = ingest_paper_sync(arxiv_id, include_frontmatter=True)
        return result.content
    except ImportError:
        pass
    finally:
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
            )
            if result.returncode == 0 and tmp.exists():
                return tmp.read_text(encoding="utf-8")
        except Exception:
            pass
        finally:
            if tmp.exists():
                tmp.unlink()

    return f"# arXiv: {arxiv_id}\n\n[arxiv2md not installed — try: pip install git+https://github.com/Linxius/arxiv2md.git]\n\nOriginal: https://arxiv.org/abs/{arxiv_id}"


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
            file_path.unlink()
            continue

        print(f"  [{ext[1:]}] {rel}")

        try:
            ok = False
            if ext == ".pdf":
                out = _convert_pdf(file_path)
                if out and out.exists():
                    converted.append(str(out.relative_to(REPO_ROOT)))
                    file_path.unlink()
                    continue
            elif ext in (".html", ".htm"):
                ok = _convert_html_file(file_path, out_file)
            elif ext in (".docx", ".doc", ".pptx", ".ppt", ".odt"):
                ok = _convert_via_pandoc(file_path, out_file)
            elif ext in (".txt", ".text", ".rst"):
                ok = _copy_text_file(file_path, out_file)
            else:
                continue

            if ok and out_file.exists():
                file_path.unlink()
                converted.append(str(out_file.relative_to(REPO_ROOT)))
            else:
                print(f"    FAILED")
        except Exception as e:
            print(f"    FAIL: {e}")

    return converted


# ─── Main ───────────────────────────────────────────────────────────

def _download_image(url: str, dest_dir: Path) -> str | None:
    """Download image from URL to dest_dir. Return filename or None on failure."""
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
    except Exception:
        return None

    # Derive filename from URL
    url_path = url.split("?")[0].rstrip("/")
    filename = os.path.basename(url_path)
    if not filename or "." not in filename:
        import uuid
        filename = f"img-{uuid.uuid4().hex[:8]}.png"

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(resp.content)
    return filename


def _fix_image_paths(md_path: Path, md_dir: Path):
    """Post-process arxiv2md output: normalize URLs, download images to figures/ and update paths.

    Linxius version outputs: ![Refer to caption](https://arxiv.org/.../figures/x.png)
    This downloads images locally and updates paths to: ![Refer to caption](figures/x.png)
    """
    if not md_path.exists():
        return
    content = md_path.read_text(encoding="utf-8")
    original = content

    # Normalize malformed arxiv HTML URLs (doubled /html/ prefix)
    content = re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', content)

    def _download_and_replace(m):
        alt = m.group(1)
        url = m.group(2)
        if not url.startswith("http"):
            return m.group(0)  # already local, skip
        filename = _download_image(url, md_dir / "figures")
        if filename:
            return f"![{alt}](figures/{filename})"
        return m.group(0)

    # Match ![alt](url) with http URLs
    content = re.sub(r'!\[([^\]]*)\]\((https?://[^)]+)\)', _download_and_replace, content)

    if content != original:
        md_path.write_text(content, encoding="utf-8")

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
        arxiv_id = extract_arxiv_id(link) or link
        # Output to subdirectory: file_dir/arxiv-{id}/paper.md + figures/
        arxiv_dir = file_dir / f"arxiv-{arxiv_id.replace('.', '')}"
        arxiv_dir.mkdir(parents=True, exist_ok=True)
        out_file = arxiv_dir / f"{slug}.md"
        content = fetch_arxiv(arxiv_id, out_path=out_file)
        content = re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', content)
        # Add related_urls to frontmatter
        related = item.get("related_urls", [])
        if related:
            related_lines = "\n".join(f"  - {r['url']}  # {r['type']}" for r in related)
            related_block = f"related_urls:\n{related_lines}\n"
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[:end] + related_block + content[end:]
            else:
                content = f"---\n{related_block}---\n{content}"
        out_file.write_text(content, encoding="utf-8")
        # Post-process: normalize URLs again (safety), download images locally
        _fix_image_paths(out_file, arxiv_dir)

        return out_file
    else:
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

        out_dir = INBOX_DIR
        for item in items:
            try:
                saved_file = process_link(item, out_dir)
                if saved_file is not None:
                    saved.append(str(saved_file.relative_to(REPO_ROOT)))
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

    # ── Step 2: local files ──
    if not no_scan:
        scan_and_convert_local_files()

    return saved


def dedup_inbox_md():
    """Deduplicate inbox.md by arxiv ID and rewrite the file.

    Groups related URLs (pdf, GitHub, project page) under the primary arxiv entry.
    Standalone items (non-arxiv, unmatched) remain as-is.
    """
    if not INBOX_MD.exists():
        print("inbox.md 不存在。")
        return

    items = read_inbox_md()
    if not items:
        print("inbox.md 为空。")
        return

    before = len(INBOX_MD.read_text(encoding="utf-8").strip().splitlines()) - 1  # minus header
    lines = ["# Inbox", ""]

    for item in items:
        related = item.get("related_urls", [])
        link = item["link"]

        # Build the main line
        raw = item.get("raw", "")
        # Try to preserve the original markdown link text
        md_match = re.search(r'\[(.+?)\]\(', raw)
        title = md_match.group(1) if md_match else link
        lines.append(f"- [{title}]({link})")

        # Add related URLs as indented sub-items
        if related:
            parts = []
            for r in related:
                rtype = r["type"]
                rurl = r["url"]
                parts.append(f"[{rtype}]({rurl})")
            lines.append(f"  - related: {', '.join(parts)}")

    lines.append("")
    content = "\n".join(lines)
    INBOX_MD.write_text(content, encoding="utf-8")

    after = len(items)
    print(f"   文件: {INBOX_MD.relative_to(REPO_ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Process inbox.md links + convert local files in inbox/")
    parser.add_argument("--list", action="store_true", help="List links without processing")
    parser.add_argument("--list-local", action="store_true", help="List local files in inbox/ without converting")
    parser.add_argument("--dedup", action="store_true", help="Deduplicate inbox.md by arxiv ID and rewrite file")
    parser.add_argument("--process-only", action="store_true", help="Only process links, skip inbox.md cleanup")
    parser.add_argument("--no-scan", action="store_true", help="Skip local file scanning")
    args = parser.parse_args()

    if args.list:
        items = read_inbox_md()
        type_labels = {"arxiv": "arXiv", "url": "web", "git": "git", "local": "local"}
        for i, item in enumerate(items, 1):
            label = type_labels.get(item["type"], item["type"])
            related = item.get("related_urls", [])
            related_str = ""
            if related:
                types = [r["type"] for r in related]
                related_str = f"  +{len(related)} related ({', '.join(types)})"
            print(f"{i}. [{label}] {item['link']}{related_str}")
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
        return

    if args.dedup:
        dedup_inbox_md()
        return

    process_inbox(process_only=args.process_only, no_scan=args.no_scan)


if __name__ == "__main__":
    main()
