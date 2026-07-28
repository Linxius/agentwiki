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
    """自动转为 phase1 模式：写 task 文件到 TASK_DIR。
    
    之前：直接退出（已弃用）。
    现在：自动创建 task 文件，agent 查看 TASK_DIR 即可 spawn 子代理处理。
    完成后运行对应脚本的 --phase2。
    """
    import hashlib
    task_id = f"auto_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
    prepare_task(task_id, prompt, max_tokens)
    print(f"📤 自动创建 task: {task_id} (phase1)")
    print(f"   请查看 {TASK_DIR}/{task_id}.json")
    print(f"   agent spawn 子代理处理后运行 --phase2")
    return ""


def auto_call_or_phase1(prompt: str, max_tokens: int = 8192, task_id: str = "auto") -> str:
    """If --phase1 is set, write task and return ''; if --phase2, read result; else auto-create task.
    
    Returns the result string (empty if task was created).
    """
    import hashlib
    if '--phase2' in sys.argv:
        return read_result(task_id)
    tid = task_id if task_id != "auto" else f"auto_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
    if '--phase1' not in sys.argv:
        print(f"  ⚠️  无 --phase1/--phase2 标志，自动创建 task: {tid}")
    call_llm(prompt, max_tokens)
    return ""


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

TASK_DIR = Path(os.environ.get("WIKI_TASK_DIR", str(REPO_ROOT / "raw" / ".tmp" / "wiki-tasks")))
RESULT_DIR = Path(os.environ.get("WIKI_RESULT_DIR", str(REPO_ROOT / "raw" / ".tmp" / "wiki-results")))


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
    Also creates RESULT_DIR so subagents have a place to write output.
    Touches a marker file so get_shared_ingest_context() regenerates its cache.
    """
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    # Touch marker to invalidate shared context cache in ingest.py
    marker = TASK_DIR.parent / "wiki-ingest-context.last"
    marker.write_text("", encoding="utf-8")
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


def write_result(task_id: str, content: str):
    """Write result + .done marker atomically.
    
    Subagents should call this (via the parent agent) to signal completion.
    The .done file lets phase2 reliably distinguish "finished with empty result"
    from "not yet written".
    """
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    txt = RESULT_DIR / f"{task_id}.txt"
    txt.write_text(content, encoding="utf-8")
    done = RESULT_DIR / f"{task_id}.done"
    done.write_text("done", encoding="utf-8")


def read_results() -> dict[str, str]:
    """Read all results from RESULT_DIR. Returns {task_id: content}.
    
    Only returns results that have a matching .done marker, to avoid
    race conditions with subagents still writing.
    """
    results = {}
    if not RESULT_DIR.exists():
        return results
    for f in RESULT_DIR.glob("*.txt"):
        done = RESULT_DIR / f"{f.stem}.done"
        if done.exists():
            results[f.stem] = f.read_text(encoding="utf-8")
    return results


def pending_tasks_done(task_ids: list[str]) -> bool:
    """Check if all expected tasks have .done markers."""
    if not RESULT_DIR.exists():
        return False
    for tid in task_ids:
        if not (RESULT_DIR / f"{tid}.done").exists():
            return False
    return True


def wait_for_tasks(task_ids: list[str], timeout: int = 600, poll: int = 5) -> bool:
    """Poll until all .done markers appear, or timeout.
    
    Returns True if all done, False if timed out.
    """
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pending_tasks_done(task_ids):
            return True
        time.sleep(poll)
    return False


def clean_task_dirs():
    """Clean up task and result directories (including .done markers and shared context)."""
    import shutil
    if TASK_DIR.exists():
        shutil.rmtree(TASK_DIR, ignore_errors=True)
    if RESULT_DIR.exists():
        shutil.rmtree(RESULT_DIR, ignore_errors=True)
    # Clean shared context cache
    tmp_dir = REPO_ROOT / "raw" / ".tmp"
    for f in tmp_dir.glob("wiki-ingest-context*"):
        f.unlink(missing_ok=True)


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


def title_to_slug(title: str) -> str:
    """Convert a paper title to a kebab-case slug for filenames.
    
    'GS-2M: Material-aware Gaussian Splatting' → 'gs-2m-material-aware-gaussian-splatting'
    """
    slug = title.lower()
    # Remove special chars except hyphens
    slug = re.sub(r'[^a-z0-9\-\u4e00-\u9fff]', '-', slug)
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def rename_file_by_title(file_path: Path) -> Path:
    """Rename a markdown file based on its first # title line.
    Returns the new path (or original if no title found).
    Used by arxiv2md/pdf2md/web fetch to produce human-readable filenames.
    """
    if not file_path.exists():
        return file_path
    content = file_path.read_text(encoding="utf-8")
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if not m:
        return file_path
    title = m.group(1).strip()
    slug = title_to_slug(title)
    if not slug:
        return file_path
    new_path = file_path.parent / f"{slug}.md"
    if new_path.exists() and new_path != file_path:
        # Don't overwrite existing; just return the original
        return file_path
    file_path.rename(new_path)
    return new_path
