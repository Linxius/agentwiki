#!/usr/bin/env python3
"""
Ingest a source document into the LLM Wiki.

Usage:
    python tools/ingest.py <path-to-source>
    python tools/ingest.py raw/articles/my-article.md
    python tools/ingest.py report.pdf                  # auto-converts to .md
    python tools/ingest.py slides.pptx notes.docx       # batch, mixed formats
    python tools/ingest.py raw/mixed/ --no-convert      # skip auto-conversion
    python tools/ingest.py --validate-only              # run validation only
    python tools/ingest.py --phase1                     # write prompts to files for subagent
    python tools/ingest.py --phase2                     # read results from subagent

Supported formats (auto-converted via markitdown):
    .pdf .docx .pptx .xlsx .html .htm .txt .csv .json .xml
    .rst .rtf .epub .ipynb .yaml .yml .tsv .wav .mp3

The LLM reads the source, extracts knowledge, and updates the wiki:
  - Creates wiki/sources/<slug>.md
  - Updates wiki/index.md
  - Updates wiki/overview.md (if warranted)
  - Creates/updates entity and concept pages
  - Appends to wiki/log.md
  - Flags contradictions
  - Runs post-ingest validation (broken links, index coverage)

Phase 1/2 file transfer protocol:
  --phase1: Build prompt and write to /tmp/wiki-tasks/ for subagent processing.
  --phase2: Read subagent results from /tmp/wiki-results/ and continue processing.
  This avoids LLM calls in the main agent; subagents handle LLM推理.
"""

import os
import re
import sys
import json
import shutil
import tempfile
import requests
from pathlib import Path
from collections import defaultdict
from datetime import date

from _utils import (read_file, write_file, call_llm, sha256,
                    parse_json_from_response, inject_source_url,
                    extract_wikilinks, all_wiki_pages,
                    prepare_tasks, read_results, clean_task_dirs, TASK_DIR)

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
LOG_FILE = WIKI_DIR / "log.md"
INDEX_FILE = WIKI_DIR / "index.md"
OVERVIEW_FILE = WIKI_DIR / "overview.md"

# File extensions that can be auto-converted to markdown via markitdown.
# .md files are ingested directly without conversion.
CONVERTIBLE_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".html", ".htm", ".txt", ".csv", ".json", ".xml",
    ".rst", ".rtf", ".epub", ".ipynb",
    ".yaml", ".yml", ".tsv",
    ".wav", ".mp3",  # audio transcription via markitdown
}
ALL_SUPPORTED_EXTENSIONS = {".md"} | CONVERTIBLE_EXTENSIONS
SCHEMA_FILE = REPO_ROOT / "AGENTS.md"
INTERESTS_FILE = REPO_ROOT / "wiki" / "interests.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def extract_url_from_file(source: Path, source_content: str) -> str | None:
    """Extract original source URL from raw file frontmatter or content.

    Priority:
    1. YAML frontmatter url: field
    2. arXiv ID in filename (e.g. 2301.12345)
    3. http URL in first 30 lines of content
    Returns None if nothing found.
    """
    fmatch = re.match(r'^---\s*\n(.*?)\n---\s*\n', source_content, re.DOTALL)
    if fmatch:
        frontmatter = fmatch.group(1)
        url_match = re.search(r'^url:\s*(.+)$', frontmatter, re.MULTILINE)
        if url_match:
            url = url_match.group(1).strip().strip('"').strip("'")
            if url:
                return url

    arxiv_match = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', source.stem)
    if arxiv_match:
        return f'https://arxiv.org/abs/{arxiv_match.group(1)}'

    lines = source_content.split('\n')
    for line in lines[:30]:
        urls = re.findall(r'https?://[^\s\)\]>"]+', line)
        for url in urls:
            if not any(skip in url for skip in ['example.com', 'localhost']):
                return url.rstrip('.,;')

    return None


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote: {path.relative_to(REPO_ROOT)}")


def build_wiki_context() -> str:
    parts = []
    if INDEX_FILE.exists():
        parts.append(f"## wiki/index.md\n{read_file(INDEX_FILE)}")
    if OVERVIEW_FILE.exists():
        parts.append(f"## wiki/overview.md\n{read_file(OVERVIEW_FILE)}")
    # Include a few recent source pages for contradiction checking
    sources_dir = WIKI_DIR / "sources"
    if sources_dir.exists():
        recent = sorted(sources_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        for p in recent:
            parts.append(f"## {p.relative_to(REPO_ROOT)}\n{p.read_text()}")
    return "\n\n---\n\n".join(parts)


def parse_interests(content: str) -> list[dict]:
    """Parse interests from wiki/interests.md content."""
    interests = []
    current_category = None
    
    for line in content.split("\n"):
        line = line.strip()
        
        cat_match = re.match(r'^## (.+)$', line)
        if cat_match:
            current_category = cat_match.group(1).strip()
            continue
        
        if line.startswith("- name:"):
            interest = {"name": line.split(":", 1)[1].strip(), "category": current_category or "未分类"}
            interests.append(interest)
        elif line.startswith("weight:") and interests:
            interests[-1]["weight"] = float(line.split(":", 1)[1].strip())
        elif line.startswith("keywords:") and interests:
            kw_str = line.split(":", 1)[1].strip()
            kw_match = re.match(r'\[(.+)\]', kw_str)
            if kw_match:
                interests[-1]["keywords"] = [k.strip() for k in kw_match.group(1).split(",")]
        elif line.startswith("description:") and interests:
            interests[-1]["description"] = line.split(":", 1)[1].strip()
    
    for interest in interests:
        interest.setdefault("weight", 0.5)
        interest.setdefault("keywords", [])
        interest.setdefault("description", "")
    
    return interests


def build_interest_extraction_prompt(created_entity_pages: list[dict],
                                    created_concept_pages: list[dict]) -> str | None:
    """Build prompt for extracting new interests from entity/concept pages.

    Returns None if there's nothing to extract.
    """
    if not created_entity_pages and not created_concept_pages:
        return None

    interests_content = read_file(INTERESTS_FILE)
    existing_interests = parse_interests(interests_content) if interests_content else []

    if not existing_interests:
        return None

    all_content = ""
    for page in created_entity_pages + created_concept_pages:
        all_content += page.get("content", "") + "\n"

    if not all_content.strip():
        return None

    schema = read_file(SCHEMA_FILE)
    interests_desc = ""
    for interest in existing_interests:
        kw_str = ", ".join(interest.get("keywords", []))
        interests_desc += f"兴趣{interest['name']}: 权重={interest['weight']}, 关键词=[{kw_str}], 描述={interest.get('description', '')}\n"

    return f"""You are extracting new research interests from wiki entity/concept pages.

Schema and conventions:
{schema}

Current interests:
{interests_desc}

New entity/concept pages created:
=== CONTENT START ===
{all_content}
=== CONTENT END ===

Analyze the new entity/concept pages and identify any NEW interests not already in the current interests list.
For each new interest, provide:

Return ONLY a valid JSON object:
{{
  "new_interests": [
    {{
      "name": "new interest name",
      "category": "existing category from interests.md or '新分类'",
      "weight": 0.7,
      "keywords": ["keyword1", "keyword2"],
      "description": "fuzzy description"
    }}
  ],
  "reason": "explanation"
}}
"""


def update_interests_from_ingest(created_entity_pages: list[dict], created_concept_pages: list[dict]):
    """Extract new interests from newly created entity/concept pages and update wiki/interests.md.

    Only adds new interests that don't already exist in interests.md.
    """
    prompt = build_interest_extraction_prompt(created_entity_pages, created_concept_pages)
    if not prompt:
        interests_content = read_file(INTERESTS_FILE)
        existing_interests = parse_interests(interests_content) if interests_content else []
        if not existing_interests:
            print("\n  提示: wiki/interests.md 为空，请先添加兴趣点。")
        return

    try:
        raw = call_llm(prompt, max_tokens=2048)
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        data = json.loads(raw)
    except Exception as e:
        print(f"  ⚠️  Interest extraction failed: {e}")
        return
    
    new_interests = data.get("new_interests", [])
    if not new_interests:
        print("\n  未发现新兴趣点。")
        return

    # Read existing interests for dedup
    interests_content = read_file(INTERESTS_FILE)
    existing_interests = parse_interests(interests_content) if interests_content else []
    existing_names = {i["name"] for i in existing_interests}

    # Filter out interests that already exist
    new_to_add = [ni for ni in new_interests if ni["name"] not in existing_names]
    
    if not new_to_add:
        print("\n  所有新兴趣已存在于 interests.md 中。")
        return
    
    # Update interests.md
    if not interests_content:
        interests_content = "# 兴趣点\n\n## 使用说明\n\n## 兴趣列表\n"
    
    # Insert new interests before the end of file
    lines = interests_content.split("\n")
    new_lines = []
    inserted = False
    
    for line in lines:
        if line.strip() == "<!-- 示例：" and not inserted:
            # Add new interests before the example comment
            for ni in new_to_add:
                new_lines.append(f"## {ni['category']}")
                new_lines.append(f"- name: {ni['name']}")
                new_lines.append(f"  weight: {ni['weight']}")
                kw_str = ", ".join(ni.get("keywords", []))
                new_lines.append(f"  keywords: [{kw_str}]")
                new_lines.append(f"  description: {ni['description']}")
                new_lines.append("")
            inserted = True
        new_lines.append(line)
    
    if not inserted:
        # Append at the end
        for ni in new_to_add:
            new_lines.append(f"## {ni['category']}")
            new_lines.append(f"- name: {ni['name']}")
            new_lines.append(f"  weight: {ni['weight']}")
            kw_str = ", ".join(ni.get("keywords", []))
            new_lines.append(f"  keywords: [{kw_str}]")
            new_lines.append(f"  description: {ni['description']}")
            new_lines.append("")
    
    # Update last_updated
    today = date.today().isoformat()
    content_str = "\n".join(new_lines)
    content_str = re.sub(
        r'(last_updated: )(.+)',
        f'\\g<1>{today}',
        content_str
    )
    
    write_file(INTERESTS_FILE, content_str)
    print(f"\n  ✅ 更新兴趣点: 新增 {len(new_to_add)} 个兴趣")
    for ni in new_to_add:
        print(f"    + {ni['name']} ({ni['category']})")


def update_index(new_entry: str, section: str = "Sources"):
    content = read_file(INDEX_FILE)
    if not content:
        content = "# Wiki Index\n\n## Overview\n- [Overview](overview.md) — living synthesis\n\n## Sources\n\n## Entities\n\n## Concepts\n\n## Syntheses\n"
    section_header = f"## {section}"

    lines = content.split("\n")
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip() == section_header:
            header_idx = i
            break

    if header_idx is None:
        content += f"\n{section_header}\n{new_entry}\n"
    else:
        # Find insertion point: skip blank lines after header
        insert_at = header_idx + 1
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        lines.insert(insert_at, new_entry)
        content = "\n".join(lines)

    write_file(INDEX_FILE, content)


def append_log(entry: str):
    existing = read_file(LOG_FILE)
    write_file(LOG_FILE, entry.strip() + "\n\n" + existing)


def validate_ingest(changed_pages: list[str] | None = None) -> dict:
    """Validate wiki integrity after an ingest.

    Checks:
      1. Broken wikilinks in changed pages (or all pages if none specified)
      2. Pages not registered in index.md

    Returns dict with 'broken_links' and 'unindexed' lists.
    """
    existing_pages = all_wiki_pages()
    index_content = read_file(INDEX_FILE).lower()

    # Determine which pages to scan for broken links
    if changed_pages:
        scan_paths = [WIKI_DIR / p for p in changed_pages if (WIKI_DIR / p).exists()]
    else:
        scan_paths = [p for p in WIKI_DIR.rglob("*.md")
                      if p.name not in ("index.md", "log.md", "lint-report.md")]

    # Check 1: Broken wikilinks
    broken_links = []
    for page_path in scan_paths:
        content = read_file(page_path)
        rel = str(page_path.relative_to(WIKI_DIR))
        for link in extract_wikilinks(content):
            # Normalize: strip paths, check stem only
            link_stem = Path(link).stem.lower() if '/' in link else link.lower()
            if link_stem not in existing_pages:
                broken_links.append((rel, link))

    # Check 2: Unindexed pages (only check changed pages)
    unindexed = []
    for p in (changed_pages or []):
        page_path = WIKI_DIR / p
        if page_path.exists():
            # Check if the page filename appears in index.md
            stem = page_path.stem.lower()
            if stem not in index_content and p not in ("log.md", "overview.md"):
                unindexed.append(p)

    return {"broken_links": broken_links, "unindexed": unindexed}


def convert_to_md(source: Path) -> Path:
    """Convert a non-markdown file to .md.

    For PDF files, delegates to tools/pdf2md.py (uses mineru/marker/etc.).
    For other formats, uses markitdown.

    Returns the path to the converted .md file (placed next to the original
    with a .md extension, or in a temp location if the source dir is read-only).
    """
    if source.suffix.lower() == ".pdf":
        # Delegate to pdf2md.py which handles PDF conversion
        import subprocess
        pdf2md_path = REPO_ROOT / "tools" / "pdf2md.py"
        print(f"  Converting PDF with pdf2md.py...")
        result = subprocess.run(
            [sys.executable, str(pdf2md_path), str(source)],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            print(f"Error: pdf2md.py failed: {result.stderr}")
            sys.exit(1)
        # pdf2md.py creates a directory <pdf_stem>/<pdf_stem>.md
        output = source.parent / source.stem / f"{source.stem}.md"
        if output.exists():
            return output
        # Fallback: search for created md file
        for md in source.parent.rglob("*.md"):
            if md.name.endswith(".md") and "images" not in str(md):
                return md
        print(f"Error: pdf2md.py did not produce output for {source.name}")
        sys.exit(1)

    try:
        from markitdown import MarkItDown
    except ImportError:
        print("Error: markitdown not installed (needed to convert non-.md files).")
        print("  Install with: pip install markitdown")
        sys.exit(1)

    md = MarkItDown(enable_plugins=False)
    try:
        result = md.convert(str(source))
    except Exception as e:
        print(f"Error: failed to convert '{source.name}': {e}")
        sys.exit(1)

    # Write converted output next to source as <name>.md
    output = source.with_suffix(".md")
    try:
        output.write_text(result.text_content, encoding="utf-8")
    except OSError:
        # Fallback: source directory may be read-only
        tmp = Path(tempfile.mkdtemp()) / f"{source.stem}.md"
        tmp.write_text(result.text_content, encoding="utf-8")
        output = tmp

    print(f"  ✓ Converted {source.name} → {output.name}")
    return output


MAX_IMAGE_SIZE = 2 * 1024 * 1024


def extract_images_from_source(content):
    """Extract (alt_text, url) from markdown source."""
    return re.findall(r'!\[(.*?)\]\((\S+?)\)', content)


def download_url_images(images, dest_dir):
    """Download URL images to dest_dir. Returns list of (url, filename, alt)."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for idx, (alt, url) in enumerate(images):
        if not url.startswith("http"):
            continue
        ext = Path(url.split('?')[0]).suffix.lower()
        if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
            ext = '.png'
        filename = f"fig{idx + 1}{ext}"
        try:
            resp = requests.get(url, headers=headers, timeout=15, stream=True)
            resp.raise_for_status()
            if len(resp.content) > MAX_IMAGE_SIZE:
                continue
            (dest_dir / filename).write_bytes(resp.content)
            downloaded.append((url, filename, alt))
        except Exception:
            continue
    return downloaded


def copy_local_images(images, source_img_dir, dest_dir):
    """Copy local images from source_img_dir to dest_dir."""
    source_img_dir = Path(source_img_dir)
    if not source_img_dir.exists():
        return []
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for idx, (alt, url) in enumerate(images):
        if url.startswith("http"):
            continue
        src = source_img_dir / url
        if src.exists() and src.stat().st_size <= MAX_IMAGE_SIZE:
            ext = src.suffix.lower()
            if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
                ext = '.png'
            filename = f"fig{idx + 1}{ext}"
            shutil.copy2(str(src), str(dest_dir / filename))
            copied.append((url, filename, alt))
    return copied


def build_ingest_image_prompt(available_images):
    """Build image section for ingest LLM prompt."""
    if not available_images:
        return ""
    parts = ["\n---\n源文档中包含以下图片，可供 wiki 页面使用："]
    for url, filename, alt in available_images:
        caption = alt if alt else '(无标题)'
        parts.append(f"- `{filename}` — {caption}")
    parts += [
        "",
        "对于选中的图片，在 source_page 中用以下格式引用：",
        "`![图片标题](images/{slug}/fig1.png)`",
        "其中 {slug} 使用你定义的 slug 字段值。",
        "判断标准：核心架构图、流程图、关键结果图等对理解本文有帮助的图片。",
    ]
    return "\n".join(parts)


def copy_referenced_images(report_content, slug, tmp_image_dir):
    """Copy images referenced in report to wiki/images/<slug>/. Returns count."""
    tmp_image_dir = Path(tmp_image_dir)
    if not tmp_image_dir.exists():
        return 0
    images_dir = WIKI_DIR / "images" / slug
    ref_pattern = re.compile(r'\]\(images/' + re.escape(slug) + r'/([^)]+)\)')
    referenced = set(ref_pattern.findall(report_content))
    if not referenced:
        shutil.rmtree(tmp_image_dir, ignore_errors=True)
        return 0
    images_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for fname in referenced:
        src = tmp_image_dir / fname
        if src.exists():
            shutil.copy2(str(src), str(images_dir / fname))
            count += 1
    shutil.rmtree(tmp_image_dir, ignore_errors=True)
    return count


def build_ingest_prompt(source_file_repo, raw_relative_path, source_url_display,
                        url_instruction, today, source_content, wiki_context,
                        schema, img_prompt_section):
    """Build the LLM prompt for ingesting a source document."""
    return f"""You are maintaining an LLM Wiki. Process this source document and integrate its knowledge into the wiki.

Schema and conventions:
{schema}

Current wiki state (index + recent pages):
{wiki_context if wiki_context else "(wiki is empty — this is the first source)"}

New source to ingest (file: {source_file_repo}):
source_file (repo-relative): {source_file_repo}
raw_relative_path: {raw_relative_path} (use this path from wiki/sources/<slug>.md to the raw file in the "## 原始出处" section)
source_url: {source_url_display}

=== SOURCE START ===
{source_content}
=== SOURCE END ===

Today's date: {today}

IMPORTANT source_page instructions:
- Use the source page format from the schema matching the file path (paper/article/book/etc).
- Set frontmatter `source_file:` to "{source_file_repo}".
- {url_instruction}
- Include a "## 原始出处" section after Summary with:
  - 原始文件: [{source_file_repo}]({raw_relative_path}) — relative link to raw file
  - 原文链接: [{{url}}]({{url}}) — original source URL (if available)
{img_prompt_section}
Return ONLY a valid JSON object with these fields (no markdown fences, no prose outside the JSON):
{{
  "title": "Human-readable title for this source",
  "slug": "kebab-case-slug-for-filename",
  "source_page": "full markdown content for wiki/sources/<slug>.md — use the source page format from the schema. CRITICAL: Aggressively convert key people, products, concepts and projects into [[Wikilinks]] inline in the text. Omitting [[ ]] for known terms is a failure.",
  "index_entry": "- [Title](sources/slug.md) — one-line summary",
  "overview_update": "full updated content for wiki/overview.md, or null if no update needed",
  "entity_pages": [
    {{"path": "entities/EntityName.md", "content": "full markdown content"}}
  ],
  "concept_pages": [
    {{"path": "concepts/ConceptName.md", "content": "full markdown content"}}
  ],
  "contradictions": ["describe any contradiction with existing wiki content, or empty list"],
  "log_entry": "## [{today}] ingest | <title>\\n\\nAdded source. Key claims: ..."
}}
"""


def ingest(source_path: str, auto_convert: bool = True):
    source = Path(source_path)
    if not source.exists():
        print(f"Error: file not found: {source_path}")
        sys.exit(1)

    # Auto-convert non-markdown files
    converted_path = None
    if source.suffix.lower() != ".md":
        if not auto_convert:
            print(f"  Skipping non-.md file (--no-convert): {source.name}")
            return
        if source.suffix.lower() not in CONVERTIBLE_EXTENSIONS:
            print(f"  ⚠️  Unsupported format: {source.suffix} — skipping {source.name}")
            print(f"       Supported: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}")
            return
        print(f"  Converting {source.name} to markdown...")
        converted_path = convert_to_md(source)
        source = converted_path

    source_content = source.read_text(encoding="utf-8")
    source_hash = sha256(source_content)
    today = date.today().isoformat()

    # Resolve original source URL
    source_url = extract_url_from_file(source, source_content)
    if not source_url:
        print(f"  ⚠️  未找到原始出处 URL")
        user_url = input(f"  请输入「{source.name}」的原始出处 URL（留空跳过）: ").strip()
        if user_url:
            source_url = user_url
            inject_source_url(source, source_url)
            print(f"  ✅ URL 已写入文件 frontmatter")

    raw_relative_path = os.path.relpath(
        str(source), str(WIKI_DIR / "sources")
    ).replace('\\', '/')
    source_file_repo = str(source.relative_to(REPO_ROOT)).replace('\\', '/')
    source_url_display = source_url or "(not found)"
    url_instruction = (
        f'- Set frontmatter `url:` to "{source_url}".'
        if source_url else
        '- If no source_url is available, set frontmatter `url:` to "" (empty string).'
    )

    print(f"\nIngesting: {source.name}  (hash: {source_hash})")

    # ── Image handling ──────────────────────────────────────────────
    tmp_img_dir = None
    img_prompt_section = ""
    images = extract_images_from_source(source_content)
    if images:
        tmp_img_dir = WIKI_DIR / ".ingest_tmp_imgs"
        all_imgs = []
        url_imgs = [(a, u) for a, u in images if u.startswith("http")]
        local_imgs = [(a, u) for a, u in images if not u.startswith("http")]
        if url_imgs:
            all_imgs.extend(download_url_images(url_imgs, tmp_img_dir))
        if local_imgs:
            sources_img_dir = source.parent / "images"
            if sources_img_dir.exists():
                all_imgs.extend(copy_local_images(local_imgs, sources_img_dir, tmp_img_dir))
        if all_imgs:
            img_prompt_section = build_ingest_image_prompt(all_imgs)
            print(f"  Found {len(all_imgs)} images for wiki use")
        else:
            shutil.rmtree(tmp_img_dir, ignore_errors=True)
            tmp_img_dir = None

    wiki_context = build_wiki_context()
    schema = read_file(SCHEMA_FILE)

    prompt = build_ingest_prompt(
        source_file_repo, raw_relative_path, source_url_display,
        url_instruction, today, source_content, wiki_context,
        schema, img_prompt_section,
    )

    # ── Phase 1: write prompt to file for subagent ──
    if "--phase1" in sys.argv:
        task_id = f"ingest_{source.stem}"
        prepare_tasks([{
            "id": task_id,
            "prompt": prompt,
            "max_tokens": 8192,
            "metadata": {
                "source_path": str(source.relative_to(REPO_ROOT)),
                "tmp_img_dir": str(tmp_img_dir) if tmp_img_dir else "",
                "today": today,
            },
        }])
        return

    # ── Phase 2: read result from subagent ──
    if "--phase2" in sys.argv:
        task_id = f"ingest_{source.stem}"
        results_map = read_results()
        raw = results_map.get(task_id, "")
        if not raw:
            print(f"Error: no result found for {task_id}")
            sys.exit(1)
        clean_task_dirs()
    else:
        # Default mode: direct LLM call
        print(f"  calling API (model: ...)")
        raw = call_llm(prompt, max_tokens=8192)

    try:
        data = parse_json_from_response(raw)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error parsing API response: {e}")
        print("Raw response saved to /tmp/ingest_debug.txt")
        Path("/tmp/ingest_debug.txt").write_text(raw)
        sys.exit(1)

    # Write source page
    slug = data["slug"]
    write_file(WIKI_DIR / "sources" / f"{slug}.md", data["source_page"])

    # Copy referenced images to wiki/images/<slug>/
    if tmp_img_dir and tmp_img_dir.exists():
        img_count = copy_referenced_images(data["source_page"], slug, tmp_img_dir)
        if img_count:
            print(f"  Images: {img_count} saved to wiki/images/{slug}/")

    # Write entity pages
    for page in data.get("entity_pages", []):
        write_file(WIKI_DIR / page["path"], page["content"])

    # Write concept pages
    for page in data.get("concept_pages", []):
        write_file(WIKI_DIR / page["path"], page["content"])

    # Update interests from new entity/concept pages
    created_entity_pages = data.get("entity_pages", [])
    created_concept_pages = data.get("concept_pages", [])
    update_interests_from_ingest(created_entity_pages, created_concept_pages)

    # Update overview
    if data.get("overview_update"):
        write_file(OVERVIEW_FILE, data["overview_update"])

    # Update index
    update_index(data["index_entry"], section="Sources")

    # Append log
    append_log(data["log_entry"])

    # Report contradictions
    contradictions = data.get("contradictions", [])
    if contradictions:
        print("\n  ⚠️  Contradictions detected:")
        for c in contradictions:
            print(f"     - {c}")

    # --- Post-ingest validation ---
    created_pages = [f"sources/{slug}.md"]
    for page in data.get("entity_pages", []):
        created_pages.append(page["path"])
    for page in data.get("concept_pages", []):
        created_pages.append(page["path"])
    updated_pages = ["index.md", "log.md"]
    if data.get("overview_update"):
        updated_pages.append("overview.md")

    validation = validate_ingest(created_pages)

    print(f"\n{'='*50}")
    print(f"  ✅ Ingested: {data['title']}")
    print(f"{'='*50}")
    print(f"  Created : {len(created_pages)} pages")
    for p in created_pages:
        print(f"           + wiki/{p}")
    print(f"  Updated : {len(updated_pages)} pages")
    for p in updated_pages:
        print(f"           ~ wiki/{p}")
    if contradictions:
        print(f"  Warnings: {len(contradictions)} contradiction(s)")
    if validation["broken_links"]:
        print(f"  ⚠️  Broken links: {len(validation['broken_links'])}")
        for page, link in validation["broken_links"][:10]:
            print(f"           wiki/{page} → [[{link}]]")
        if len(validation["broken_links"]) > 10:
            print(f"           ... and {len(validation['broken_links']) - 10} more")
    if validation["unindexed"]:
        print(f"  ⚠️  Not in index.md: {len(validation['unindexed'])}")
        for p in validation["unindexed"][:10]:
            print(f"           wiki/{p}")
        if len(validation["unindexed"]) > 10:
            print(f"           ... and {len(validation['unindexed']) - 10} more")
    if not validation["broken_links"] and not validation["unindexed"]:
        print("  ✓ Validation passed — no broken links, all pages indexed")
    print()


def run_from_digest(date_str: str = None):
    """Process files from digest/YYYY-MM-DD/brief.md marked for wiki ingest.
    
    1. Read brief.md to find entries marked "[x] 合入 wiki"
    2. Show list to user for category confirmation
    3. Move files to appropriate category directory
    4. Call ingest() for each file
    """
    from datetime import date as _date
    today_str = _date.today().isoformat()
    
    digest_dir = REPO_ROOT / "raw" / "digest"
    brief_file = digest_dir / "brief.md"
    
    if not brief_file.exists():
        print("brief.md not found. Run filter.py first.")
        return
    
    brief_content = read_file(brief_file)
    
    # Parse entries with "[x] 合入 wiki"
    entries = []
    lines = brief_content.split('\n')
    i = 0
    while i < len(lines):
        if (lines[i].startswith('#### ') or lines[i].startswith('### ')) and not lines[i].startswith('### ['):
            title = lines[i][4:].strip() if lines[i].startswith('#### ') else lines[i][4:].strip()
            
            # Check if this entry is for the specified date
            if date_str:
                found = False
                for j in range(max(0, i-10), i):
                    if date_str in lines[j]:
                        found = True
                        break
                if not found:
                    i += 1
                    continue
            
            # Collect entry lines
            entry_lines = []
            next_i = i + 1
            while next_i < len(lines) and not re.match(r'^#{2,4} ', lines[next_i]):
                entry_lines.append(lines[next_i])
                next_i += 1
            
            if re.search(r'\[x\]\s*合入 wiki|\[X\]\s*合入 wiki', '\n'.join(entry_lines)):
                # Extract source URL from entry
                source_url = ''
                for el in entry_lines:
                    m = re.match(r'- 来源:\s*(.*)', el)
                    if m:
                        source_url = m.group(1).strip()
                        break
                entries.append({
                    'title': title,
                    'source_url': source_url,
                })
            
            i = next_i
        else:
            i += 1
    
    if not entries:
        print("No entries marked for wiki ingest.")
        return
    
    print(f"Found {len(entries)} entries marked for wiki ingest:\n")
    
    # Try to find files in sources/
    date_to_process = date_str or today_str
    sources_dir = digest_dir / "sources" / date_to_process
    
    processed_files = []
    for entry in entries:
        title = entry['title']
        # Try to find matching file
        found_file = None
        if sources_dir.exists():
            for f in sources_dir.iterdir():
                if title in f.name or f.name.startswith(title.split('.')[0]):
                    found_file = f
                    break
        
        if found_file:
            entry['file_path'] = found_file
            entry['current_path'] = str(found_file.relative_to(REPO_ROOT))
            processed_files.append(entry)
        else:
            print(f"⚠️  File not found for: {title}")
            print(f"  Looking in: {sources_dir}")
    
    if not processed_files:
        print("No files found to ingest.")
        return
    
    # Show what will be ingested and ask for category confirmation
    print("=" * 60)
    print("文件确认 (Files to ingest):")
    print("=" * 60)
    for entry in processed_files:
        cat = entry.get('suggested_category', 'papers')
        print(f"\n- {entry['title']}")
        print(f"  当前路径: {entry['current_path']}")
        print(f"  建议分类: {cat}/")
    
    print("\n" + "=" * 60)
    confirm = input("确认合入 wiki? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("已取消。")
        return
    
    # Ingest each file
    print("\n开始合入 wiki...")
    for entry in processed_files:
        file_path = entry['file_path']
        print(f"\nIngesting: {file_path.name}")
        
        # Get category from entry or use suggestion
        category = entry.get('suggested_category', 'papers')
        
        # If destination has same file, skip
        dest_dir = REPO_ROOT / "raw" / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / file_path.name
        
        if dest_path.exists():
            print(f"  目标已存在: {dest_path.relative_to(REPO_ROOT)}，跳过")
            continue
        
        # Move file to category directory
        shutil.move(str(file_path), str(dest_path))
        print(f"  移动: {dest_path.relative_to(REPO_ROOT)}")

        # Inject source URL into the file before ingest
        if entry.get('source_url'):
            inject_source_url(dest_path, entry['source_url'])
        
        # Run actual ingest
        ingest(str(dest_path), auto_convert=True)
        
        processed_files.append(entry)
        # Update status
    
    print("\n✅ 合入完成！")


if __name__ == "__main__":
    # Handle --validate-only flag
    if len(sys.argv) == 2 and sys.argv[1] == "--validate-only":
        print("Running wiki validation (no ingest)...\n")
        result = validate_ingest()
        if result["broken_links"]:
            print(f"Broken wikilinks: {len(result['broken_links'])}")
            for page, link in result["broken_links"][:20]:
                print(f"  wiki/{page} → [[{link}]]")
            if len(result["broken_links"]) > 20:
                print(f"  ... and {len(result['broken_links']) - 20} more")
        else:
            print("No broken wikilinks found.")
        print()
        pages = all_wiki_pages()
        index_content = read_file(INDEX_FILE).lower()
        unindexed_all = []
        for p in WIKI_DIR.rglob("*.md"):
            if p.name in ("index.md", "log.md", "lint-report.md", "overview.md"):
                continue
            if p.stem.lower() not in index_content:
                unindexed_all.append(str(p.relative_to(WIKI_DIR)))
        if unindexed_all:
            print(f"Pages not in index.md: {len(unindexed_all)}")
            for up in unindexed_all[:20]:
                print(f"  wiki/{up}")
            if len(unindexed_all) > 20:
                print(f"  ... and {len(unindexed_all) - 20} more")
        else:
            print("All pages are indexed.")
        sys.exit(0)

    # Parse flags
    no_convert = "--no-convert" in sys.argv
    from_digest = "--from-digest" in sys.argv
    date_str = None
    
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--from-digest" and i+1 < len(sys.argv[1:]):
            next_arg = sys.argv[1:][i+1]
            if not next_arg.startswith("--") and len(next_arg) == 10:
                date_str = next_arg
    
    # Handle --from-digest mode
    if from_digest:
        print("Processing files from digest/ for wiki ingest...\n")
        run_from_digest(date_str)
        sys.exit(0)
    
    if not args:
        print("Usage: python tools/ingest.py <path-to-source> [path2 ...] [dir1 ...]")
        print("       python tools/ingest.py --validate-only")
        print("       python tools/ingest.py --from-digest [YYYY-MM-DD]  # ingest from digest brief")
        print("       python tools/ingest.py --no-convert  # skip auto-conversion of non-.md files")
        print("       python tools/ingest.py --phase1  # write prompts to files for subagent processing")
        print("       python tools/ingest.py --phase2  # read results from subagent processing")
        print(f"\nSupported formats: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    paths_to_process = []
    for arg in args:
        p = Path(arg)
        if p.is_file():
            ext = p.suffix.lower()
            if ext in ALL_SUPPORTED_EXTENSIONS:
                paths_to_process.append(p)
            else:
                print(f"  ⚠️  Skipping unsupported format: {p.name} ({ext})")
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix.lower() in ALL_SUPPORTED_EXTENSIONS:
                    paths_to_process.append(f)
        else:
            import glob
            for f in glob.glob(arg, recursive=True):
                g_p = Path(f)
                if g_p.is_file() and g_p.suffix.lower() in ALL_SUPPORTED_EXTENSIONS:
                    paths_to_process.append(g_p)

    # Deduplicate while preserving order
    unique_paths = []
    seen = set()
    for p in paths_to_process:
        abs_p = p.resolve()
        if abs_p not in seen:
            seen.add(abs_p)
            unique_paths.append(p)

    if not unique_paths:
        print("Error: no supported files found to ingest.")
        print(f"Supported formats: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    if len(unique_paths) > 1:
        print(f"Batch mode: found {len(unique_paths)} files to ingest.")

    for p in unique_paths:
        ingest(str(p), auto_convert=not no_convert)
