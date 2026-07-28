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
    python tools/ingest.py --paper <arxiv-id-or-url>    # direct paper ingest (skip inbox)
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
  --phase1: Build prompt and write to raw/.tmp/wiki-tasks/ for subagent processing.
  --phase2: Read subagent results from raw/.tmp/wiki-results/ and continue processing.
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
                    prepare_tasks, read_results, clean_task_dirs, TASK_DIR,
                    rename_file_by_title)

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


_SHARED_CONTEXT_FILE = "wiki-ingest-context.md"
_SHARED_CACHE_MARKER = "wiki-ingest-context.last"  # timestamp marker
_SHARED_CONTEXT_PATH = None  # module-level cache for get_shared_ingest_context()


def get_shared_ingest_context() -> Path | None:
    """Write shared schema + wiki context to a file subagents can read independently.
    Returns the path, or None if writing fails. 
    
    Cache is invalidated when prepare_tasks() is called (checked via marker file mtime).
    """
    global _SHARED_CONTEXT_PATH
    shared_dir = REPO_ROOT / "raw" / ".tmp"
    shared_path = shared_dir / _SHARED_CONTEXT_FILE
    marker_file = shared_dir / _SHARED_CACHE_MARKER
    
    # Check if cache is still valid: for current process, keep using it (module-level cache)
    if _SHARED_CONTEXT_PATH and _SHARED_CONTEXT_PATH.exists():
        # But also check if prepare_tasks() was called since cache was built
        if marker_file.exists() and _SHARED_CONTEXT_PATH.exists():
            cache_mtime = _SHARED_CONTEXT_PATH.stat().st_mtime
            marker_mtime = marker_file.stat().st_mtime
            if marker_mtime <= cache_mtime:
                return _SHARED_CONTEXT_PATH
        else:
            return _SHARED_CONTEXT_PATH

    shared_dir.mkdir(parents=True, exist_ok=True)
    
    schema = read_file(SCHEMA_FILE)
    wiki_context = build_wiki_context()
    
    content = f"""# 共享 Wiki 上下文（子代理读此文件而非内联）
 
## Schema and conventions（Wiki 体系结构与模板约定）
 
{schema}
 
## Current wiki state（当前索引 + 近期页面）
 
{wiki_context or "(wiki is empty — this is the first source)"}
"""
    shared_path.write_text(content, encoding="utf-8")
    _SHARED_CONTEXT_PATH = shared_path
    return shared_path



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
            return
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
        return

    # Read existing interests for dedup
    interests_content = read_file(INTERESTS_FILE)
    existing_interests = parse_interests(interests_content) if interests_content else []
    existing_names = {i["name"] for i in existing_interests}

    # Filter out interests that already exist
    new_to_add = [ni for ni in new_interests if ni["name"] not in existing_names]
    
    if not new_to_add:
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


def _append_to_overview(bullet: str):
    """Append a bullet point to the overview page.

    Reads current overview.md, finds the last section,
    and appends the bullet before the next section or at end of file.
    Never overwrites the full file.
    """
    from datetime import date as _date
    content = read_file(OVERVIEW_FILE)
    today_str = _date.today().isoformat()
    if not content:
        # No overview yet — create minimal structure
        content = f"""---
title: "Overview"
type: synthesis
tags: []
sources: []
last_updated: "{today_str}"
---

# Overview

当前 wiki 包含以下已合入的源文档：

### 论文

"""
    # Find insertion point: end of the last section (before next ### or end)
    lines = content.split("\n")
    # Find the last non-empty line that is not a section header
    insert_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith("### ") or stripped.startswith("## "):
            # Insert after the content before this header
            insert_idx = i
            break
    # If we hit a header, insert right before it (end of previous section)
    # OR append at the very end
    if bullet.startswith("- ") or bullet.startswith("  - "):
        lines.insert(insert_idx, bullet)
    else:
        lines.insert(insert_idx, f"- {bullet}")
    write_file(OVERVIEW_FILE, "\n".join(lines))


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
        print(f"Error: markitdown not installed.")
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
    parts = ["\n---\n源文档中包含以下图片，可供 wiki 页面引用："]
    for url, filename, alt in available_images:
        caption = alt if alt else '(无标题)'
        parts.append(f"- `{filename}` — {caption} (URL: {url})")
    parts += [
        "",
        "图片引用规则（优先使用 arxiv HTML URL，如 `https://arxiv.org/html/XXXX.XXXXX/figures/images/xxx.png`，URL 更稳定且节省空间）：",
        "1. 在 source_page 中用 `![描述](images/{slug}/fig1.png)` 引用下载到本地的图片",
        "2. 也可以直接引用 arxiv 原始 URL：`![描述](https://arxiv.org/html/.../figures/images/xxx.png)`",
        "",
        "选择标准（严格按优先级）：",
        "  P0 - 方法框架图/管线图/架构图：必须选中，放在 ## Method 第一行（紧跟标题之后，在 ### 子节之前）",
        "  P1 - 关键结果对比图/效果图：可选，放在 ## Results 或 ## Comparisons 中",
        "  P2 - 消融实验图/可视化：可选，放在 ## Ablations 中",
        "  ❌ 不选：实验结果表格截图、作者头像、数据集示例图（与wiki无关的）",
        "",
        "Method 章节中，框架图必须是第一个内容元素：",
        "  ## Method",
        "  ",
        "  ![框架图描述](images/{slug}/fig1.png)",
        "  ",
        "  ### 整体思路",
        "  ...",
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
                        url_instruction, today, source_content,
                        img_prompt_section, shared_context_path: str = "",
                        comments: str = "", deepdive_path: str = "",
                        brief_entry_ref: str = "",
                        source_content_path: str = ""):
    """Build the LLM prompt for ingesting a source document.
    
    When shared_context_path is set, the subagent reads schema + wiki context
    from that file instead of receiving it inline (saves ~68KB per task).
    
    When source_content is very large (>20KB) and source_content_path is set,
    the full source is NOT inlined — subagent reads it via its own Read tool.
    
    Args:
        comments: User/agent comments/insights to incorporate into wiki
        deepdive_path: Path to deep-read report for this entry
        brief_entry_ref: Brief.md entry reference (date + title)
        source_content_path: If set, subagent reads source from this file path
    """
    context_section = (
        f"Read shared wiki context from `{shared_context_path}` "
        "(README there defines schema, conventions, templates, and current wiki state)."
        if shared_context_path
        else "(wiki is empty — this is the first source)"
    )
    
    # Comments/insights section (optional)
    comments_section = ""
    if comments or deepdive_path or brief_entry_ref:
        parts = ["\n---\n### 补充信息（必须合入 wiki）"]
        if brief_entry_ref:
            parts.append(f"- Brief 条目引用: {brief_entry_ref}")
        if deepdive_path:
            parts.append(f"- 深度阅读报告: [{deepdive_path}]({deepdive_path})")
        if comments:
            parts.append(f"- 评论/启示: {comments}")
        parts.append(
            "\n请将以上评论和启示整合到 wiki 页面的 `## 评论与启示` 章节中。"
            "使用 `os.path.relpath()` 计算所有链接的相对路径。"
        )
        comments_section = "\n".join(parts)
    
    INLINE_THRESHOLD = 20000
    if source_content_path and len(source_content) > INLINE_THRESHOLD:
        source_section = (
            f"(Source is large — {len(source_content)} chars. Read it directly:)\n\n"
            f"Read the file `{source_content_path}` to get the full source content."
        )
    else:
        source_section = source_content
    
    return f"""You are maintaining an LLM Wiki. Process this source document and integrate its knowledge into the wiki.

Schema and conventions:
{context_section}

New source to ingest (file: {source_file_repo}):
source_file (repo-relative): {source_file_repo}
raw_relative_path: {raw_relative_path} (use this path from wiki/sources/<slug>.md to the raw file in the "## 原始出处" section)
source_url: {source_url_display}
{comments_section}

=== SOURCE START ===
{source_section}
=== SOURCE END ===

Today's date: {today}

IMPORTANT source_page instructions:
- Use the source page format from the schema matching the file path (paper/article/book/etc).
- Set frontmatter `source_file:` to "{source_file_repo}".
- {url_instruction}
- Include a "## 原始出处" section after Summary with:
  - 原始文件: [{source_file_repo}]({raw_relative_path}) — relative link to raw file
  - 原文链接: [{{url}}]({{url}}) — original source URL (if available)
  - Brief 条目: [{brief_entry_ref or 'brief.md'}](brief_entry_ref) — if available
  - 深度阅读报告: [{deepdive_path or 'N/A'}]({deepdive_path}) — if available
{img_prompt_section}
Return ONLY a valid JSON object with these fields (no markdown fences, no prose outside the JSON):
{{
  "title": "Human-readable title for this source",
  "slug": "kebab-case-slug-for-filename",
  "source_page": "full markdown content for wiki/sources/<slug>.md — use the source page format from the schema. CRITICAL: Aggressively convert key people, products, concepts and projects into [[Wikilinks]] inline in the text. Omitting [[ ]] for known terms is a failure.",
  "index_entry": "- [Title](sources/slug.md) — one-line summary",
  "overview_update": "single bullet point to append to wiki/overview.md (e.g. \"- [[Title|slug]] — description\"), or null if no update needed",
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


def ingest(source_path: str, auto_convert: bool = True,
           comments: str = "", deepdive_path: str = "",
           brief_entry_ref: str = ""):
    source = Path(source_path).resolve()
    if not source.exists():
        print(f"Error: file not found: {source_path}")
        sys.exit(1)

    # Auto-convert non-markdown files
    converted_path = None
    if source.suffix.lower() != ".md":
        if not auto_convert:
            return
        if source.suffix.lower() not in CONVERTIBLE_EXTENSIONS:
            print(f"Error: unsupported format {source.suffix}")
            return
        converted_path = convert_to_md(source)
        source = converted_path

    source_content = source.read_text(encoding="utf-8")
    source_hash = sha256(source_content)
    today = date.today().isoformat()

    # Resolve original source URL
    source_url = extract_url_from_file(source, source_content)
    if not source_url:
        if sys.stdin.isatty() and '--phase1' not in sys.argv:
            print(f"  ⚠️  未找到原始出处 URL")
            user_url = input(f"  请输入「{source.name}」的原始出处 URL（留空跳过）: ").strip()
            if user_url:
                source_url = user_url
                inject_source_url(source, source_url)
        else:
            pass

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
        else:
            shutil.rmtree(tmp_img_dir, ignore_errors=True)
            tmp_img_dir = None

    # Use shared context file for --phase1 to save ~68KB/task of repeated schema
    shared_ctx_path = get_shared_ingest_context()
    shared_ctx_arg = str(shared_ctx_path.relative_to(REPO_ROOT)) if shared_ctx_path else ""

    prompt = build_ingest_prompt(
        source_file_repo, raw_relative_path, source_url_display,
        url_instruction, today, source_content,
        img_prompt_section, shared_context_path=shared_ctx_arg,
        comments=comments, deepdive_path=deepdive_path,
        brief_entry_ref=brief_entry_ref,
        source_content_path=source_file_repo,
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
    else:
        raw = call_llm(prompt, max_tokens=8192)
        if not raw:
            return

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
        copy_referenced_images(data["source_page"], slug, tmp_img_dir)

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

    # Update overview (append bullet, never overwrite full file)
    if data.get("overview_update"):
        _append_to_overview(data["overview_update"].strip())

    # Update index
    update_index(data["index_entry"], section="Sources")

    # Append log
    append_log(data["log_entry"])

    # Report contradictions
    contradictions = data.get("contradictions", [])

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
    broken = len(validation["broken_links"])
    unindexed = len(validation["unindexed"])
    warn = f", {broken} broken links" if broken else ""
    warn += f", {unindexed} unindexed" if unindexed else ""
    print(f"  [{slug}] {len(created_pages)} created, {len(updated_pages)} updated{warn}")


def _parse_entry_from_brief(lines: list[str], start_i: int, entry_lines: list[str]) -> dict:
    """Parse a single brief.md entry into a structured dict."""
    entry = {'title': '', 'source_url': '', 'domain': '', 'keywords': '', 'source_file': '',
             'comments': '', 'detailed_report': ''}
    title_line = lines[start_i]
    if title_line.startswith('#### '):
        entry['title'] = title_line[5:].strip()
    elif title_line.startswith('### '):
        entry['title'] = title_line[4:].strip()
    
    entry_text = '\n'.join(entry_lines)
    
    for el in entry_lines:
        m = re.match(r'- 来源:\s*(.*)', el)
        if m:
            entry['source_url'] = m.group(1).strip()
        m = re.match(r'- 领域:\s*(.*)', el)
        if m:
            entry['domain'] = m.group(1).strip()
        m = re.match(r'- 关键词:\s*(.*)', el)
        if m:
            entry['keywords'] = m.group(1).strip()
        m = re.match(r'- 源文件:\s*\[([^\]]+)\]', el)
        if m:
            entry['source_file'] = m.group(1).strip()
    
    # Extract detailed report / comments
    detailed_match = re.search(r'\*\*详细报告\*\*\s*[:：]?\s*(.+?)(?=\n\n|\n###|\n####|$)', entry_text, re.DOTALL)
    if detailed_match:
        entry['detailed_report'] = detailed_match.group(1).strip()
    
    # Extract any user-written comments (lines after detailed report, before next entry)
    # These are free-text comments/notes the user wrote
    if entry['detailed_report']:
        rest = entry_text.split(detailed_match.group(0), 1)[-1].strip()
        # Skip URLs, empty lines, and markdown formatting
        user_lines = []
        for line in rest.split('\n'):
            line = line.strip()
            if line and not line.startswith('![') and not line.startswith('https://') and not line.startswith('- 源'):
                user_lines.append(line)
        if user_lines:
            entry['comments'] = ' '.join(user_lines)
    
    return entry


def _group_entries_for_merge(entries: list[dict]) -> list[list[dict]]:
    """Group entries that should be merged into a single wiki page.
    
    Merge criteria (descending priority):
    1. Same non-empty source_url
    2. Same domain + source filenames share ≥2 meaningful words (≥3 chars)
    """
    GENERIC_WORDS = {'for', 'and', 'the', 'on', 'at', 'in', 'with', 'to', 'of', 'a',
                     'from', 'by', 'via', 'using', 'based', 'real', 'time', 'end',
                     'new', 'novel', 'toward', 'towards', 'method', 'approach',
                     'model', 'data', 'image', 'scene', 'neural', 'learning',
                     'high', 'low', 'large', 'small', 'fast', 'rendering'}
    
    def filename_words(name: str) -> set:
        stem = Path(name).stem.lower()
        words = set(re.findall(r'[a-z]+', stem))
        return {w for w in words if len(w) >= 3 and w not in GENERIC_WORDS}
    
    groups: list[list[dict]] = []
    used = set()
    
    for i, a in enumerate(entries):
        if i in used:
            continue
        group = [a]
        used.add(i)
        a_words = filename_words(a.get('source_file', ''))
        
        for j, b in enumerate(entries):
            if j in used:
                continue
            # Criterion 1: same non-empty source_url
            if a.get('source_url') and a['source_url'] == b.get('source_url'):
                group.append(b)
                used.add(j)
            # Criterion 2: same domain + keyword overlap in filenames
            elif a.get('domain') and a['domain'] and a['domain'] == b.get('domain'):
                b_words = filename_words(b.get('source_file', ''))
                if len(a_words & b_words) >= 2:
                    group.append(b)
                    used.add(j)
        
        groups.append(group)
    
    return groups


def _find_deepdive_for_entry(entry: dict, brief_date: str | None) -> str:
    """Find deep-read report for a brief entry. Returns relpath string or empty string."""
    if not brief_date:
        return ""
    title = entry.get('title', '')
    if not title:
        return ""
    safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in title)
    slug = safe_title.lower().replace('__', '-').replace('_', '-')
    
    # Search in deepdive directories
    deepdive_base = REPO_ROOT / "raw" / "digest" / "deepdive"
    if not deepdive_base.exists():
        return ""
    
    for d in sorted(deepdive_base.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        candidate = d / f"{slug}.md"
        if candidate.exists():
            rel = os.path.relpath(str(candidate), str(REPO_ROOT)).replace('\\', '/')
            return rel
    
    return ""
    
    
def _combine_source_files(file_paths: list[Path]) -> Path | None:
    """Combine multiple source files into one temp file with section headers."""
    combined_parts = []
    for fp in file_paths:
        if not fp or not fp.exists():
            continue
        content = read_file(fp)
        title_hint = fp.stem.replace('-', ' ').title()
        combined_parts.append(f"## {title_hint}\n\n{content}")
    
    if not combined_parts:
        return None
    
    combined = "\n\n---\n\n".join(combined_parts)
    temp = REPO_ROOT / "raw" / "digest" / f"_merged_{Path(file_paths[0]).stem}.md"
    write_file(temp, combined)
    return temp


def run_from_digest(date_str: str = None, auto_yes: bool = False):
    """Process files from digest/YYYY-MM-DD/brief.md marked for wiki ingest.
    
    1. Read brief.md to find entries marked "[x] 合入 wiki"
    2. Show list to user for category confirmation, with merge suggestions
    3. Move files to appropriate category directory
    4. Call ingest() for each file (merged groups → single ingest)
    """
    from datetime import date as _date
    today_str = _date.today().isoformat()
    
    digest_dir = REPO_ROOT / "raw" / "digest"
    brief_file = digest_dir / "brief.md"
    
    if not brief_file.exists():
        print("brief.md not found. Run filter.py first.")
        return
    
    brief_content = read_file(brief_file)
    
    # Detect brief date from header (e.g. "# 资讯简报  YYYY-MM-DD")
    brief_date_match = re.search(r'#\s+资讯简报\s+(\d{4}-\d{2}-\d{2})', brief_content[:200])
    brief_date = brief_date_match.group(1) if brief_date_match else None
    
    # Clean up analysis-results.json — no longer needed after brief is confirmed
    for f in (digest_dir / "analysis-results.json", digest_dir / "analysis-results.jsonc"):
        if f.exists():
            f.unlink()
    
    # If date_str specified, skip briefs that don't match
    if date_str and brief_date and brief_date != date_str:
        print(f"Date mismatch: {brief_date} != {date_str}")
        return
    
    # Parse entries with "[x] 合入 wiki"
    entry_re = re.compile(r'^#{2,4} ')
    entries = []
    lines = brief_content.split('\n')
    i = 0
    while i < len(lines):
        if (lines[i].startswith('#### ') or lines[i].startswith('### ')) and not lines[i].startswith('### ['):
            # Collect entry lines
            entry_lines = []
            next_i = i + 1
            while next_i < len(lines) and not re.match(r'^#{2,4} ', lines[next_i]):
                entry_lines.append(lines[next_i])
                next_i += 1
            
            if re.search(r'\[x\]\s*合入 wiki|\[X\]\s*合入 wiki', '\n'.join(entry_lines)):
                entries.append(_parse_entry_from_brief(lines, i, entry_lines))
            
            i = next_i
        else:
            i += 1
    
    if not entries:
        print("No entries marked for wiki ingest.")
        return

    # Resolve file paths — search across all date dirs in sources/
    sources_base = digest_dir / "sources"
    for entry in entries:
        source_file = entry.get('source_file', '')
        if not source_file:
            continue
        candidate = Path(source_file)
        if candidate.exists():
            entry['file_path'] = candidate
            entry['current_path'] = source_file
        else:
            # Search across all date subdirectories
            fname = candidate.name
            found = None
            for d in sorted(sources_base.iterdir()):
                if d.is_dir() and d.name != ".gitkeep":
                    candidate_path = d / fname
                    if candidate_path.exists():
                        found = candidate_path
                        break
            if found:
                entry['file_path'] = found
                entry['current_path'] = str(found.relative_to(REPO_ROOT))
    
    # Remove entries without resolvable files
    entries = [e for e in entries if e.get('file_path')]
    
    if not entries:
        print("No source files found to ingest.")
        return
    
    # ── Merge detection ──
    merged_groups = _group_entries_for_merge(entries)
    total_items = sum(len(g) for g in merged_groups)
    if total_items != len(entries):
        merged_groups = [[e] for e in entries]

    # Determine category for each entry (all default to 'papers')
    for group in merged_groups:
        cat = 'papers'
        for e in group:
            e['category'] = cat

    # ── Ingest ──
    
    # run_from_digest always uses --phase1 workflow (direct LLM calls are deprecated)
    if '--phase1' not in sys.argv:
        sys.argv.append('--phase1')
    
    for group in merged_groups:
        if len(group) > 1:
            # ── Merged group: combine files, ingest once ──
            file_paths = [e['file_path'] for e in group if e.get('file_path')]
            combined = _combine_source_files(file_paths)
            if not combined:
                continue
            
            # Determine slug from first entry's source file
            first_slug = Path(file_paths[0]).stem
            category = group[0].get('category', 'papers')
            dest_dir = REPO_ROOT / "raw" / category
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / f"{first_slug}.md"
            
            if dest_path.exists():
                continue
            else:
                shutil.move(str(combined), str(dest_path))
                
                # Inject source URLs
                urls = [e.get('source_url', '') for e in group if e.get('source_url')]
                if urls:
                    inject_source_url(dest_path, urls[0])
                
                # Collect comments from all merged entries
                comments = '; '.join([e.get('comments', '') for e in group if e.get('comments')])
                
                # Find deepdive report path
                deepdive_path = _find_deepdive_for_entry(group[0], brief_date)
                
                # Build brief entry reference
                brief_ref = f"brief.md {brief_date} > {group[0].get('title', '')}"
                
                ingest(str(dest_path), auto_convert=True,
                       comments=comments, deepdive_path=deepdive_path,
                       brief_entry_ref=brief_ref)
        else:
            # ── Single entry ──
            entry = group[0]
            file_path = entry['file_path']
            
            category = entry.get('category', 'papers')
            dest_dir = REPO_ROOT / "raw" / category
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / file_path.name
            
            if dest_path.exists():
                continue
            
            shutil.copy2(str(file_path), str(dest_path))
            
            if entry.get('source_url'):
                inject_source_url(dest_path, entry['source_url'])
            
            # Collect comments and deepdive reference
            comments = entry.get('comments', '')
            deepdive_path = _find_deepdive_for_entry(entry, brief_date)
            brief_ref = f"brief.md {brief_date} > {entry.get('title', '')}"
            
            try:
                ingest(str(dest_path), auto_convert=True,
                       comments=comments, deepdive_path=deepdive_path,
                       brief_entry_ref=brief_ref)
                # Only remove source after successful ingest
                file_path.unlink()
            except Exception:
                raise

    # ── Update brief.md: mark entries as ingested + auto-archive ──
    _brief_file = REPO_ROOT / "raw" / "digest" / "brief.md"
    if _brief_file.exists():
        import sys as _sys
        _sys.path.insert(0, str(REPO_ROOT / "tools"))
        from brief import mark_entry_done, run_archive
        _content = _brief_file.read_text(encoding="utf-8")
        titles_done = set()
        for group in merged_groups:
            for e in group:
                title = e.get('title', '').strip()
                if title:
                    _content = mark_entry_done(_content, title, '合入 wiki')
                    titles_done.add(title)
        _brief_file.write_text(_content, encoding="utf-8")
        if titles_done:
            print(f"\n📝 brief.md: {len(titles_done)} entries marked as 已合入")
        # Auto-archive completed date groups
        archived = run_archive()
        if archived:
            print(f"  ✅ 已归档: {', '.join(archived)}")


# ── arXiv patterns (shared with deep-read.py) ──
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


def _refetch_arxiv(arxiv_id: str, tmp_dir: Path) -> Path | None:
    """Fetch arXiv paper content via arxiv2md, with retry + fallbacks."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_file = tmp_dir / f"arxiv-{arxiv_id}.md"
    if out_file.exists():
        return out_file

    # Check if raw/papers/ already has a substantial file for this arxiv_id
    papers_dir = REPO_ROOT / "raw" / "papers"
    if papers_dir.exists():
        for existing in papers_dir.glob("*.md"):
            if arxiv_id in existing.stem:
                content = existing.read_text(encoding="utf-8")
                if len(content) > 5000:
                    return existing

    # Try arxiv2md with retry on 429
    import time
    for attempt in range(3):
        try:
            from arxiv2md import ingest_paper_sync
            result = ingest_paper_sync(arxiv_id)
            import re as _re
            content = _re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', result.content)
            out_file.write_text(content, encoding="utf-8")
            renamed = rename_file_by_title(out_file)
            return renamed
        except ImportError:
            break  # arxiv2md not installed, skip to fallback
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 10 * (attempt + 1)
                import time as _time
                _time.sleep(wait)
            elif attempt < 2:
                import time as _time
                _time.sleep(5)
            else:
                pass
    else:
        # Reset for next fallback (avoid continuing in the for-else)
        pass
    try:
        from arxiv2md import ingest_paper_sync
    except ImportError:
        pass
    finally:
        cache_dir = REPO_ROOT / ".arxiv2md_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)

    # Fallback 1: fetch HTML via webfetch (more complete than API abstract)
    try:
        import requests as _req
        html_url = f"https://arxiv.org/html/{arxiv_id}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = _req.get(html_url, headers=headers, timeout=30)
        resp.raise_for_status()
        # Try trafilatura for markdown extraction
        text_content = resp.text
        try:
            import trafilatura
            md = trafilatura.extract(text_content, include_comments=False, include_tables=True) or ""
            if len(md) > 2000:
                content = f"# arXiv {arxiv_id}\n\n{md}\n\nOriginal: https://arxiv.org/abs/{arxiv_id}\n"
                out_file.write_text(content, encoding="utf-8")
                renamed = rename_file_by_title(out_file)
                return renamed
        except ImportError:
            pass
        # Fallback within fallback: extract via regex from HTML
        import re as _re2
        body_match = _re2.search(r'<body[^>]*>(.*?)</body>', text_content, _re2.DOTALL)
        if body_match:
            body = body_match.group(1)
            # Remove script/style
            body = _re2.sub(r'<script[^>]*>.*?</script>', '', body, flags=_re2.DOTALL)
            body = _re2.sub(r'<style[^>]*>.*?</style>', '', body, flags=_re2.DOTALL)
            body = _re2.sub(r'<[^>]+>', ' ', body)
            body = _re2.sub(r'\s+', ' ', body).strip()
            if len(body) > 2000:
                content = f"# arXiv {arxiv_id}\n\n{body}\n\nOriginal: https://arxiv.org/abs/{arxiv_id}\n"
                out_file.write_text(content, encoding="utf-8")
                renamed = rename_file_by_title(out_file)
                return renamed
    except Exception:
        pass

    # Fallback 2: fetch abstract from arXiv API
    try:
        import requests as _req
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        resp = _req.get(url, timeout=30)
        resp.raise_for_status()
        import xml.etree.ElementTree as ET
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.content)
        entry = root.find("atom:entry", ns)
        if entry is not None:
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ").replace("  ", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ").replace("  ", " ")
            content = f"""# {title}

**arXiv**: https://arxiv.org/abs/{arxiv_id}

**Abstract**:
{summary}
"""
            out_file.write_text(content, encoding="utf-8")
            renamed = rename_file_by_title(out_file)
            return renamed
    except Exception:
        pass

    out_file.write_text(f"# arXiv: {arxiv_id}\n\n[Unable to fetch content]\n\nOriginal: https://arxiv.org/abs/{arxiv_id}\n", encoding="utf-8")
    out_file_renamed = rename_file_by_title(out_file)
    return out_file_renamed


def _refetch_web(url: str, tmp_dir: Path) -> Path | None:
    """Fetch web page content."""
    import hashlib
    slug = hashlib.md5(url.encode()).hexdigest()[:12]
    out_file = tmp_dir / f"web-{slug}.md"
    if out_file.exists():
        return out_file

    try:
        import requests as _req
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = _req.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'

        title = ""
        m = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()

        try:
            import trafilatura
            md = trafilatura.extract(resp.text, include_comments=False, include_tables=True) or ""
        except ImportError:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                md = soup.get_text(separator="\n", strip=True)
            except ImportError:
                md = resp.text[:10000]

        content = f"# {title or 'Untitled'}\n\n{md}\n\n原始链接: {url}\n"
        out_file.write_text(content, encoding="utf-8")
        if title:
            renamed = rename_file_by_title(out_file)
            return renamed
        return out_file
    except Exception as e:
        out_file.write_text(f"# Error: {url}\n\n{e}\n", encoding="utf-8")
        return out_file


def run_direct_ingest(paper_input: str):
    """Direct ingest: fetch paper from arxiv/PDF/web URL, then ingest into wiki.
    
    Skips inbox/filter/deep-read stages entirely.
    """
    today = date.today().isoformat()
    tmp_base = REPO_ROOT / "raw" / ".tmp" / "direct-ingest"
    tmp_dir = tmp_base / today
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Detect input type
    arxiv_id = extract_arxiv_id(paper_input)
    is_pdf = paper_input.lower().endswith('.pdf')
    is_url = paper_input.startswith('http')

    if arxiv_id:
        file_path = _refetch_arxiv(arxiv_id, tmp_dir)
        source_url = f"https://arxiv.org/abs/{arxiv_id}"
    elif is_pdf:
        pdf_path = Path(paper_input).resolve()
        if not pdf_path.exists():
            print(f"Error: PDF not found: {pdf_path}")
            return
        import subprocess
        pdf2md_path = REPO_ROOT / "tools" / "pdf2md.py"
        result = subprocess.run(
            [sys.executable, str(pdf2md_path), str(pdf_path)],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            print(f"Error: pdf2md failed")
            return
        # Find generated md
        output_dir = pdf_path.parent / pdf_path.stem
        file_path = None
        if output_dir.exists():
            for f in output_dir.rglob("*.md"):
                if f.name != pdf_path.stem:
                    continue
                file_path = f
                break
        if not file_path:
            for f in pdf_path.parent.rglob("*.md"):
                if f.stem == pdf_path.stem:
                    file_path = f
                    break
        if not file_path or not file_path.exists():
            print(f"Error: pdf2md did not produce output")
            return
        source_url = str(pdf_path)
    elif is_url:
        file_path = _refetch_web(paper_input, tmp_dir)
        source_url = paper_input
    else:
        print(f"Error: unrecognized input: {paper_input}")
        return

    if not file_path or not file_path.exists():
        print(f"Error: failed to fetch content")
        return

    # Copy to raw/papers/ for persistent storage
    dest_dir = REPO_ROOT / "raw" / "papers"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file_path.name
    shutil.copy2(str(file_path), str(dest_path))

    # Inject source URL into frontmatter
    inject_source_url(dest_path, source_url)

    # Ingest directly
    ingest(str(dest_path), auto_convert=True)


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
    direct_paper = "--paper" in sys.argv
    date_str = None
    
    # Handle --paper mode
    if direct_paper:
        paper_idx = sys.argv.index("--paper")
        if paper_idx + 1 < len(sys.argv):
            paper_input = sys.argv[paper_idx + 1]
            run_direct_ingest(paper_input)
            sys.exit(0)
        else:
            print("Error: --paper requires a URL, arxiv ID, or path argument")
            sys.exit(1)
    
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--from-digest" and i+1 < len(sys.argv[1:]):
            next_arg = sys.argv[1:][i+1]
            if not next_arg.startswith("--") and len(next_arg) == 10:
                date_str = next_arg
    
    # Handle --from-digest mode
    if from_digest:
        auto_yes = "--yes" in sys.argv
        print("Processing files from digest/ for wiki ingest...\n")
        run_from_digest(date_str, auto_yes=auto_yes)
        sys.exit(0)
    
    if not args and not from_digest and not direct_paper:
        print("Usage: python tools/ingest.py <path-to-source> [path2 ...] [dir1 ...]")
        print("       python tools/ingest.py --validate-only")
        print("       python tools/ingest.py --from-digest [YYYY-MM-DD]  # ingest from digest brief")
        print("       python tools/ingest.py --paper <arxiv-id-or-url>   # direct paper ingest")
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
