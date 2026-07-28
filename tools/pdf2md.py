#!/usr/bin/env python3
"""
Convert PDF or arXiv sources to Markdown for the raw/ directory.

Usage:
    python tools/pdf2md.py <input> [--output raw/papers/output.md] [--backend auto]

Inputs:
    arXiv ID      →  2401.12345
    arXiv URL     →  https://arxiv.org/abs/2401.12345
    Local PDF     →  /path/to/paper.pdf

Backends:
    auto          →  arXiv inputs use arxiv2md; PDFs use mineru (fallback: marker, pymupdf4llm — currently disabled)
    arxiv2md      →  Best for arXiv papers (uses structured source, not PDF)
    mineru        →  Best for general PDFs (CLI tool with OCR support)
    marker        →  Best for complex multi-column academic PDFs (disabled)
    pymupdf4llm   →  Fast, lightweight, no GPU — good for native-text PDFs (disabled)

Examples:
    python tools/pdf2md.py 2401.12345
    python tools/pdf2md.py https://arxiv.org/abs/2401.12345
    python tools/pdf2md.py paper.pdf --backend mineru
    python tools/pdf2md.py paper.pdf -o raw/papers/my-paper.md
"""

import argparse
import importlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "raw" / "inbox"

ARXIV_PATTERNS = [
    re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$"),                          # 2401.12345
    re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5})(v\d+)?"),              # URL form
    re.compile(r"arxiv\.org/pdf/(\d{4}\.\d{4,5})(v\d+)?"),              # PDF URL
]


def extract_title_from_md(md_path: Path) -> str:
    """Extract the first H1 title from a markdown file."""
    content = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return Path(md_path).stem


def extract_arxiv_id(source: str) -> str | None:
    """Return arXiv ID if input looks like an arXiv reference, else None."""
    for pattern in ARXIV_PATTERNS:
        m = pattern.search(source)
        if m:
            return m.group(1)
    return None


def check_dependency(package: str, pip_name: str | None = None) -> bool:
    """Check if a Python package is importable."""
    try:
        importlib.import_module(package)
        return True
    except ImportError:
        return False


def install_hint(pip_name: str) -> str:
    return f"  Install with: pip install {pip_name}"


# ─── Backend: arxiv2md ──────────────────────────────────────────────

def convert_arxiv(arxiv_id: str, output: Path) -> Path:
    """Convert arXiv paper using arxiv2md (structured source, not PDF)."""
    pip_name = "arxiv2markdown"
    if not check_dependency("arxiv2md", pip_name):
        print(f"Error: arxiv2md not installed.\n{install_hint(pip_name)}")
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["arxiv2md", arxiv_id, "-o", str(output)])

    if result.returncode != 0:
        print(f"Error: arxiv2md failed with exit code {result.returncode}")
        sys.exit(1)

    # Normalize malformed arxiv HTML URLs (doubled /html/ prefix) in the output
    if output.exists():
        raw = output.read_text(encoding="utf-8")
        fixed = re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', raw)
        if fixed != raw:
            output.write_text(fixed, encoding="utf-8")

    # Clean up arxiv2md cache
    cache_dir = REPO_ROOT / ".arxiv2md_cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)

    return output


# ─── Backend: marker ────────────────────────────────────────────────

def convert_marker(pdf_path: Path, output: Path) -> Path:
    """Convert PDF using marker (high-fidelity, handles complex layouts)."""
    pip_name = "marker-pdf"
    if not check_dependency("marker", pip_name):
        print(f"Error: marker not installed.\n{install_hint(pip_name)}")
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    # marker outputs to a directory; we move the result to the target path
    tmp_dir = output.parent / f".marker_tmp_{output.stem}"
    result = subprocess.run(["marker_single", str(pdf_path), "--output_dir", str(tmp_dir)])

    if result.returncode != 0:
        print(f"Error: marker failed with exit code {result.returncode}")
        sys.exit(1)

    # marker creates <pdf_name>/<pdf_name>.md inside output_dir
    md_files = list(tmp_dir.rglob("*.md"))
    if not md_files:
        print("Error: marker produced no markdown output.")
        sys.exit(1)

    # Move first .md to target, clean up
    md_files[0].rename(output)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return output


# ─── Backend: pymupdf4llm ───────────────────────────────────────────

def convert_pymupdf(pdf_path: Path, output: Path) -> Path:
    """Convert PDF using pymupdf4llm (fast, lightweight, native-text PDFs)."""
    pip_name = "pymupdf4llm"
    if not check_dependency("pymupdf4llm", pip_name):
        print(f"Error: pymupdf4llm not installed.\n{install_hint(pip_name)}")
        sys.exit(1)

    import pymupdf4llm

    output.parent.mkdir(parents=True, exist_ok=True)
    md_text = pymupdf4llm.to_markdown(str(pdf_path))
    output.write_text(md_text, encoding="utf-8")

    return output


# ─── Backend: mineru ────────────────────────────────────────────────

def convert_mineru(pdf_path: Path, output: Path) -> Path:
    """Convert PDF using mineru, output to <pdf_parent>/<title>/ with md and images/."""
    if not shutil.which("mineru"):
        print(f'Error: mineru not installed.\n  Install with: pip install -U "mineru[all]"')
        sys.exit(1)

    tmp_dir = output.parent / f".mineru_tmp_{output.stem}"
    env = os.environ.copy()
    result = subprocess.run(["mineru", "-p", str(pdf_path), "-o", str(tmp_dir), "--method", "ocr"], env=env)

    if result.returncode != 0:
        print(f"Error: mineru failed with exit code {result.returncode}")
        sys.exit(1)

    # Find the md file in mineru output (mineru creates <pdf_name>/<pdf_name>.md)
    md_files = list(tmp_dir.rglob("*.md"))
    if not md_files:
        print("Error: mineru produced no markdown output.")
        sys.exit(1)

    # Extract title from the first markdown file
    title = extract_title_from_md(md_files[0])
    title_slug = slugify(title)

    # Create final directory: <pdf_parent>/<title_slug>/
    final_dir = pdf_path.parent / title_slug
    final_dir.mkdir(parents=True, exist_ok=True)

    # Rename PDF to title-based name, keep in final directory
    renamed_pdf = final_dir / f"{title_slug}.pdf"
    shutil.move(str(pdf_path), str(renamed_pdf))

    # Move markdown to final dir with title-based name
    md_files[0].rename(final_dir / f"{title_slug}.md")

    # Move images directory if it exists
    images_dir = tmp_dir / "images"
    if images_dir.exists():
        shutil.move(str(images_dir), final_dir / "images")
    # Also check for images inside the mineru output subdirectory
    for img_dir in tmp_dir.rglob("images"):
        if img_dir.is_dir():
            dest = final_dir / "images"
            if not dest.exists():
                shutil.move(str(img_dir), dest)
            break

    # Clean up temp directory
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return final_dir / f"{title_slug}.md"


# ─── Auto-detect & dispatch ─────────────────────────────────────────

BACKENDS = {
    "mineru": convert_mineru,
    "arxiv2md": convert_arxiv,
    # "marker": convert_marker,
    # "pymupdf4llm": convert_pymupdf,
}


def slugify(name: str) -> str:
    """Turn a filename or arXiv ID into a safe kebab-case slug."""
    name = Path(name).stem if "." in name else name
    name = re.sub(r"[^\w\s-]", "", name.lower())
    return re.sub(r"[\s_]+", "-", name).strip("-")


def resolve_output(source: str, arxiv_id: str | None, output_arg: str | None, backend: str = "auto") -> Path:
    """Determine the output path: raw/inbox/<slug>/<slug>.md"""
    if output_arg:
        p = Path(output_arg)
        return p if p.is_absolute() else REPO_ROOT / p

    if arxiv_id:
        slug = slugify(arxiv_id)
    else:
        slug = slugify(Path(source).stem)

    out_dir = DEFAULT_OUTPUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{slug}.md"


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF/arXiv to Markdown for raw/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="arXiv ID, arXiv URL, or path to a PDF file")
    parser.add_argument("-o", "--output", help="Output .md path (default: raw/papers/<slug>.md)")
    parser.add_argument(
        "-b", "--backend",
        choices=["auto", "mineru", "arxiv2md"],
        default="auto",
        help="Conversion backend (default: auto-detect)",
    )
    args = parser.parse_args()

    backend = args.backend
    arxiv_id = extract_arxiv_id(args.input)

    # ── Auto-select backend ──
    if backend == "auto":
        if arxiv_id:
            backend = "arxiv2md"
        elif shutil.which("mineru"):
            backend = "mineru"
        # elif check_dependency("marker"):
        #     backend = "marker"
        # elif check_dependency("pymupdf4llm"):
        #     backend = "pymupdf4llm"
        else:
            print("\nError: No conversion backend found.")
            print("Install one of:")
            print('  MINERU_MODEL_SOURCE=modelscope pip install -U "mineru[all]"  # for PDFs (recommended)')
            print("  pip install arxiv2markdown   # for arXiv papers")
            sys.exit(1)

    output = resolve_output(args.input, arxiv_id, args.output, backend)

    # ── Check if already converted ──
    if output.exists():
        return

    # ── Dispatch ──
    if backend == "arxiv2md":
        if not arxiv_id:
            print("Error: arxiv2md backend requires an arXiv ID or URL.")
            sys.exit(1)
        convert_arxiv(arxiv_id, output)
    else:
        pdf_path = REPO_ROOT / args.input if not Path(args.input).is_absolute() else Path(args.input)
        if not pdf_path.exists():
            print(f"Error: file not found: {args.input}")
            sys.exit(1)
        BACKENDS[backend](pdf_path, output)


if __name__ == "__main__":
    main()
