#!/usr/bin/env python3
"""
Auto-fetch missing/empty source files referenced in brief.md.

Usage:
    python tools/fetch-sources.py              # process all entries in brief.md
    python tools/fetch-sources.py --date YYYY-MM-DD  # process specific date

Flow:
    1. Read raw/digest/brief.md
    2. For each entry with a source_path:
       - If file missing or empty (0 bytes) → re-fetch from source_url
       - arxiv → arxiv2md
       - web URL → requests + trafilatura
       - PDF → pdf2md.py
    3. Update brief.md source_path if file was re-fetched to a new location

Output:
    - Fetched source files in raw/digest/sources/YYYY-MM-DD/
    - Updated brief.md with corrected source_path
"""

import re
import sys
import argparse
import hashlib
from pathlib import Path
from datetime import date

REPO_ROOT = Path(__file__).parent.parent
DIGEST_DIR = REPO_ROOT / "raw" / "digest"
BRIEF_FILE = DIGEST_DIR / "brief.md"
TOOLS_DIR = REPO_ROOT / "tools"

ARXIV_PATTERNS = [
    re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"arxiv\.org/pdf/(\d{4}\.\d{4,5})(v\d+)?"),
    re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$"),
]


def extract_arxiv_id(text: str) -> str | None:
    for p in ARXIV_PATTERNS:
        m = p.search(text)
        if m:
            return m.group(1)
    return None


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def fetch_arxiv(arxiv_id: str, out_path: Path) -> bool:
    """Fetch arxiv paper via arxiv2md, fallback to API abstract."""
    try:
        from arxiv2md import ingest_paper_sync
        result = ingest_paper_sync(arxiv_id)
        write_file(out_path, result.content)
        return True
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: arxiv API abstract
    try:
        import requests
        import xml.etree.ElementTree as ET
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.content)
        entry = root.find("atom:entry", ns)
        if entry is not None:
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ").replace("  ", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ").replace("  ", " ")
            content = f"# {title}\n\n**arXiv**: https://arxiv.org/abs/{arxiv_id}\n\n**Abstract**:\n{summary}\n"
            write_file(out_path, content)
            return True
    except Exception:
        pass

    return False


def fetch_web(url: str, out_path: Path) -> bool:
    """Fetch web page via requests + trafilatura."""
    try:
        import requests
        import trafilatura
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"

        title = ""
        m = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()

        md = trafilatura.extract(resp.text, include_comments=False, include_tables=True) or ""
        if not md:
            md = resp.text[:5000]

        header = f"# {title}\n\n**URL**: {url}\n\n" if title else f"**URL**: {url}\n\n"
        write_file(out_path, header + md)
        return True
    except Exception:
        return False


def fetch_pdf(url: str, out_path: Path) -> bool:
    """Fetch PDF via pdf2md.py."""
    pdf2md = TOOLS_DIR / "pdf2md.py"
    if not pdf2md.exists():
        return False
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, str(pdf2md), url, "-o", str(out_path)],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


def parse_brief_entries(brief_content: str, date_str: str = None) -> list[dict]:
    """Parse brief.md entries, return list of {title, source_url, source_path, line_range}."""
    HEADER = re.compile(r'^#{3,4} (.+)')
    entries = []
    lines = brief_content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]
        header_match = HEADER.match(line)
        if header_match and not line.lstrip().startswith("### ["):
            file_title = header_match.group(1).strip()

            if date_str:
                found_date = False
                for j in range(max(0, i - 10), i):
                    if date_str in lines[j]:
                        found_date = True
                        break
                if not found_date:
                    i += 1
                    continue

            entry_start = i
            entry_lines = []
            next_i = i + 1
            while next_i < len(lines):
                if HEADER.match(lines[next_i]) and not lines[next_i].lstrip().startswith("### ["):
                    break
                entry_lines.append(lines[next_i])
                next_i += 1

            entry_text = "\n".join(entry_lines)

            source_url = ""
            url_match = re.search(r"- 来源:\s*(.+)", entry_text)
            if url_match:
                source_url = url_match.group(1).strip()

            source_path = ""
            path_match = re.search(r"- 源文件:\s*(.+)", entry_text)
            if path_match:
                source_path = path_match.group(1).strip()

            entries.append({
                "title": file_title,
                "source_url": source_url,
                "source_path": source_path,
                "line_start": entry_start,
                "line_end": next_i,
                "entry_text": entry_text,
            })

            i = next_i
        else:
            i += 1

    return entries


def needs_fetch(file_path: Path) -> bool:
    """Check if file is missing or empty."""
    if not file_path.exists():
        return True
    if file_path.stat().st_size == 0:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Auto-fetch missing source files in brief.md")
    parser.add_argument("--date", type=str, help="Process entries from specific date (YYYY-MM-DD)")
    args = parser.parse_args()

    if not BRIEF_FILE.exists():
        print("brief.md 不存在。")
        return

    brief_content = read_file(BRIEF_FILE)
    if not brief_content.strip():
        print("brief.md 为空。")
        return

    today = date.today().isoformat()
    date_str = args.date or today

    entries = parse_brief_entries(brief_content, date_str)
    if not entries:
        print("未找到条目。")
        return

    # Filter entries that have source_path
    entries_with_path = [e for e in entries if e["source_path"]]
    if not entries_with_path:
        print("所有条目均无源文件路径。")
        return

    print(f"检查 {len(entries_with_path)} 个条目的源文件...\n")

    fetched = 0
    skipped = 0
    failed = 0
    updated_brief = brief_content

    for entry in entries_with_path:
        source_path_str = entry["source_path"]
        source_url = entry["source_url"]
        title = entry["title"]

        # Resolve source_path relative to REPO_ROOT
        file_path = REPO_ROOT / source_path_str

        if not needs_fetch(file_path):
            skipped += 1
            continue

        if not source_url:
            print(f"  ⚠️  {title}: 源文件缺失且无 source_url，跳过")
            failed += 1
            continue

        print(f"  🔄 {title}: 源文件为空/缺失，重新抓取...")

        # Determine fetch strategy from source_url
        arxiv_id = extract_arxiv_id(source_url)
        success = False

        if arxiv_id:
            out_path = file_path if file_path.parent.exists() else (DIGEST_DIR / "sources" / date_str / file_path.name)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            success = fetch_arxiv(arxiv_id, out_path)
        elif source_url.lower().endswith(".pdf"):
            out_path = file_path if file_path.parent.exists() else (DIGEST_DIR / "sources" / date_str / file_path.name)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            success = fetch_pdf(source_url, out_path)
        elif source_url.startswith("http"):
            out_path = file_path if file_path.parent.exists() else (DIGEST_DIR / "sources" / date_str / file_path.name)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            success = fetch_web(source_url, out_path)
        else:
            print(f"    ⚠️  无法识别 source_url 类型: {source_url}")
            failed += 1
            continue

        if success:
            fetched += 1
            print(f"    ✅ 已抓取: {out_path.relative_to(REPO_ROOT)}")
        else:
            failed += 1
            print(f"    ❌ 抓取失败")

    print(f"\n✅ 完成: {fetched} 抓取, {skipped} 跳过(已存在), {failed} 失败")


if __name__ == "__main__":
    main()
