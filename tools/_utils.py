#!/usr/bin/env python3
"""Shared utilities for wiki tools."""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = REPO_ROOT / "wiki"


def read_file(path):
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def call_llm(prompt, max_tokens=8192):
    try:
        from litellm import completion
    except ImportError:
        print("Error: litellm not installed. Run: pip install litellm")
        sys.exit(1)

    model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-latest")

    kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    response = completion(**kwargs)
    return response.choices[0].message.content


def parse_json_from_response(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in response")
    return json.loads(match.group())


def extract_wikilinks(content):
    return re.findall(r'\[\[([^\]]+)\]\]', content)


def all_wiki_pages():
    pages = set()
    for p in WIKI_DIR.rglob("*.md"):
        if p.name not in ("index.md", "log.md", "lint-report.md", "health-report.md"):
            pages.add(p.stem.lower())
    return pages


def inject_source_url(file_path, source_url):
    if not source_url or source_url == file_path.as_posix():
        return

    content = read_file(file_path)
    fmatch = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

    if fmatch:
        frontmatter = fmatch.group(1)
        rest = content[fmatch.end():]

        if re.search(r'^url:\s*', frontmatter, re.MULTILINE):
            frontmatter = re.sub(
                r'^url:\s*.*$', f'url: {source_url}',
                frontmatter, flags=re.MULTILINE,
            )
        else:
            first_nl = frontmatter.index('\n') + 1 if '\n' in frontmatter else len(frontmatter)
            frontmatter = frontmatter[:first_nl] + f'url: {source_url}\n' + frontmatter[first_nl:]

        new_content = f'---\n{frontmatter}\n---\n{rest}'
    else:
        new_content = f'---\nurl: {source_url}\n---\n{content}'

    file_path.write_text(new_content, encoding='utf-8')
