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


def _load_config():
    config_path = REPO_ROOT / "config.json"
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8")
        # Strip JS-style // line comments before parsing
        raw = re.sub(r"(?m)^\s*//.*$", "", raw)
        return json.loads(raw)
    return {}


def call_llm(prompt, max_tokens=8192):
    """直接 LLM 调用已弃用。请使用 --phase1/--phase2 工作流：脚本写 prompt 到文件，agent spawn 子代理处理。"""
    print("Error: 直接 LLM 调用已弃用。请使用 --phase1/--phase2 工作流。")
    print("  python tools/<script>.py --phase1  # 生成 prompt 文件")
    print("  # agent spawn 子代理处理 /tmp/wiki-tasks/*.json")
    print("  python tools/<script>.py --phase2  # 读取结果继续处理")
    sys.exit(1)


def parse_json_from_response(text):
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in response")
    return json.loads(match.group())


def extract_wikilinks(content):
    return re.findall(r'\[\[([^\]]+)\]\]', content)


# ── File-based task protocol ──
# Scripts write prompts to files, agent spawns subagents to process them,
# subagents write results back to files. Agent never reads large content.

TASK_DIR = Path(os.environ.get("WIKI_TASK_DIR", "/tmp/wiki-tasks"))
RESULT_DIR = Path(os.environ.get("WIKI_RESULT_DIR", "/tmp/wiki-results"))


def prepare_task(task_id: str, prompt: str, max_tokens: int = 8192,
                 metadata: dict = None) -> Path:
    """Write prompt to file, return the file path."""
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    task_file = TASK_DIR / f"{task_id}.json"
    payload = {
        "id": task_id,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "metadata": metadata or {},
    }
    task_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return task_file


def prepare_tasks(tasks: list[dict]) -> Path:
    """Write multiple tasks, return manifest path.

    Each task dict: {id, prompt, max_tokens, metadata}
    """
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"tasks": []}
    for t in tasks:
        prepare_task(t["id"], t["prompt"], t.get("max_tokens", 8192), t.get("metadata"))
        manifest["tasks"].append({
            "id": t["id"],
            "prompt_file": str(TASK_DIR / f"{t['id']}.json"),
        })
    manifest_path = TASK_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📤 {len(tasks)} 个任务已写入 {TASK_DIR}")
    return manifest_path


def read_result(task_id: str) -> str:
    """Read result content from file."""
    result_file = RESULT_DIR / f"{task_id}.txt"
    if result_file.exists():
        return result_file.read_text(encoding="utf-8")
    return ""


def read_results() -> dict[str, str]:
    """Read all results from RESULT_DIR. Returns {task_id: content}."""
    results = {}
    if RESULT_DIR.exists():
        for f in RESULT_DIR.glob("*.txt"):
            results[f.stem] = f.read_text(encoding="utf-8")
    return results


def clean_task_dirs():
    """Clean up task and result directories."""
    import shutil
    if TASK_DIR.exists():
        shutil.rmtree(TASK_DIR, ignore_errors=True)
    if RESULT_DIR.exists():
        shutil.rmtree(RESULT_DIR, ignore_errors=True)


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
