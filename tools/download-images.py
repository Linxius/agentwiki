#!/usr/bin/env python3
"""
Download external images referenced in wiki source pages to local wiki/images/.

Usage:
    python tools/download-images.py <source-slug>
    python tools/download-images.py my-paper
    python tools/download-images.py all       # process all source pages

Scans wiki/sources/<slug>.md for:
  - ![](url) and ![alt](url)
  - <img src="url">
  - data:image/ base64 embeddings

Downloads each to wiki/images/<slug>/ and updates paths.
"""

import base64
import imghdr
import os
import re
import sys
import uuid
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO_ROOT / "wiki" / "sources"
IMAGES_DIR = REPO_ROOT / "wiki" / "images"

# Match external image URLs in markdown and HTML img tags
IMG_PATTERNS = [
    (re.compile(r'!\[([^\]]*)\]\((https?://[^)\s]+)\)'), "markdown"),
    (re.compile(r'<img\s+[^>]*src="(https?://[^"]+)"', re.IGNORECASE), "html"),
    (re.compile(r'!\[([^\]]*)\]\((data:image/[^)\s]+)\)'), "markdown_base64"),
    (re.compile(r'<img\s+[^>]*src="(data:image/[^"]+)"', re.IGNORECASE), "html_base64"),
]


def slug_from_path(p):
    """Extract slug from path: wiki/sources/<slug>.md or wiki/sources/<slug>/ch-*.md"""
    rel = p.relative_to(SOURCES_DIR)
    parts = rel.parts
    if len(parts) >= 2:
        return parts[0]  # book slug (directory)
    return p.stem


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def download_image(url, dest_dir, filename=None):
    """Download image from URL, return local path. Handle base64."""
    if url.startswith("data:image/"):
        # Base64 embedded image
        match = re.match(r'data:image/(\w+);base64,(.+)', url)
        if not match:
            return None
        ext = match.group(1)
        b64_data = match.group(2)
        try:
            img_bytes = base64.b64decode(b64_data)
        except Exception:
            return None
        if not filename:
            filename = f"img-{uuid.uuid4().hex[:8]}.{ext}"
        dest = dest_dir / filename
        dest.write_bytes(img_bytes)
        return filename

    # External URL
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ⚠️  Failed to download {url}: {e}")
        return None

    if not filename:
        # Derive filename from URL
        url_path = url.split("?")[0].rstrip("/")
        filename = os.path.basename(url_path)
        if not filename or "." not in filename:
            filename = f"img-{uuid.uuid4().hex[:8]}.png"

    dest = dest_dir / filename
    dest.write_bytes(resp.content)
    return filename


def process_source_page(page_path):
    """Process a single source page for images."""
    slug = slug_from_path(page_path)
    image_dir = IMAGES_DIR / slug
    ensure_dir(image_dir)

    content = page_path.read_text(encoding="utf-8")
    original = content
    replacements = []

    for pattern, img_type in IMG_PATTERNS:
        for match in pattern.finditer(content):
            url = match.group(2) if img_type in ("markdown", "html") else match.group(2)
            alt = match.group(1) if img_type.startswith("markdown") else ""

            if url.startswith("data:image/"):
                # Base64 — encode with unique filename
                img_match = re.match(r'data:image/(\w+);base64,(.+)', url)
                ext = img_match.group(1) if img_match else "png"
                fname = f"img-{uuid.uuid4().hex[:8]}.{ext}"
            else:
                # URL — derive filename
                url_path = url.split("?")[0].rstrip("/")
                fname = os.path.basename(url_path)
                if not fname or "." not in fname:
                    fname = f"img-{uuid.uuid4().hex[:8]}.png"

            local_path = download_image(url, image_dir, fname)
            if not local_path:
                continue

            # Build relative path from source page to image
            # wiki/sources/<slug>.md → ../images/<slug>/filename
            # wiki/sources/<book>/ch-*.md → ../images/<book>/filename
            rel_path = f"../images/{slug}/{local_path}"

            if img_type == "markdown":
                new = f"![{alt}]({rel_path})"
            elif img_type == "markdown_base64":
                new = f"![{alt}]({rel_path})"
            elif img_type == "html":
                new = f'<img src="{rel_path}" alt="{alt}" />'
            else:
                new = f'<img src="{rel_path}" alt="{alt}" />'

            replacements.append((match.group(0), new))
            print(f"  {'→'.ljust(3)} {os.path.basename(local_path)}")

    # Apply replacements
    for old, new in replacements:
        content = content.replace(old, new, 1)

    if content != original:
        page_path.write_text(content, encoding="utf-8")
        print(f"  ✅ Updated paths in {page_path.relative_to(REPO_ROOT)}")

    return len(replacements)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/download-images.py <slug|all>")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "all":
        pages = []
        for p in SOURCES_DIR.rglob("*.md"):
            if p.parent == SOURCES_DIR:
                pages.append(p)  # flat source pages
            elif p.parent.name == "sources" and p.parent != SOURCES_DIR:
                pages.append(p)  # book sub-pages
        pages.sort()
    else:
        # Single slug: check as flat file or book directory
        flat = SOURCES_DIR / f"{arg}.md"
        book_dir = SOURCES_DIR / arg
        pages = []
        if flat.exists():
            pages.append(flat)
        if book_dir.exists():
            pages.extend(sorted(book_dir.glob("*.md")))
        if not pages:
            print(f"Source page not found: {arg}")
            sys.exit(1)

    total = 0
    for p in pages:
        slug = slug_from_path(p)
        print(f"\n[{slug}] {p.relative_to(REPO_ROOT)}")
        count = process_source_page(p)
        total += count

    if total > 0:
        print(f"\nDone. Downloaded {total} images to wiki/images/.")
    else:
        print("\nNo external images found.")


if __name__ == "__main__":
    main()
