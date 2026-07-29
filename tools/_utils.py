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
    return ""


def auto_call_or_phase1(prompt: str, max_tokens: int = 8192, task_id: str = "auto") -> str:
    import hashlib
    if '--phase2' in sys.argv:
        return read_result(task_id)
    tid = task_id if task_id != "auto" else f"auto_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
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
    return manifest_path


def read_result(task_id: str) -> str:
    """Read result content from file (supports .txt and .json)."""
    for ext in (".txt", ".json"):
        result_file = RESULT_DIR / f"{task_id}{ext}"
        if result_file.exists():
            return result_file.read_text(encoding="utf-8")
    return ""


def write_result(task_id: str, content: str):
    """Write result + .done marker atomically.
    
    Creates two files:
      RESULT_DIR/{task_id}.txt     — the result content
      RESULT_DIR/{task_id}.done    — completion marker (empty file)
    
    read_results() globs *.txt and checks matching {stem}.done.
    DO NOT create files manually — always call this function.
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
    
    Supports both .txt and .json result files (with matching .done marker).
    Auto-creates RESULT_DIR if it doesn't exist.
    """
    results = {}
    if not RESULT_DIR.exists():
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        return results
    for pattern in ("*.txt", "*.json"):
        for f in RESULT_DIR.glob(pattern):
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


def safe_download_arxiv(arxiv_id: str, out_path: Path) -> str:
    """Download arXiv paper via arxiv2md CLI, handling the -o directory quirk.
    
    arxiv2md's -o flag creates a DIRECTORY with the given name and puts the
    actual file inside as <Title>.md. This wrapper: passes a directory to -o,
    globs for the output file, validates content length (≥5000), and renames
    to out_path. Falls back to Python API on CLI failure.
    
    Caches results in raw/.tmp/arxiv-cache/<arxiv_id>.md to avoid re-download.
    
    Returns content string. Raises RuntimeError if both CLI and API fail.
    """
    import shutil, subprocess, sys

    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Remove any leftover directory from a previous -o mistake
    if out_path.exists() and out_path.is_dir():
        shutil.rmtree(out_path, ignore_errors=True)

    # ── Cache check ──
    CACHE_BASE = REPO_ROOT / "raw" / ".tmp" / "arxiv-cache"
    cache_dir = CACHE_BASE / arxiv_id
    cache_path = cache_dir / f"{arxiv_id}.md"
    if cache_path.exists():
        content = cache_path.read_text(encoding="utf-8")
        out_path.write_text(content, encoding="utf-8")
        print(f"  📦 使用缓存: {cache_path}")
        return content

    # ── CLI mode: arxiv2md <id> -o <dir> → outputs to <dir>/<Title>.md ──
    try:
        result = subprocess.run(
            [sys.executable, "-m", "arxiv2md", arxiv_id,
             "--frontmatter", "--remove-toc",
             "-o", str(out_dir)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            md_files = list(out_dir.glob("*.md"))
            if md_files:
                generated = md_files[0]
                content = generated.read_text(encoding="utf-8")
                if len(content) >= 5000:
                    if generated != out_path:
                        generated.rename(out_path)
                    # Write to cache
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(content, encoding="utf-8")
                    return content
                print(f"  ⚠️  arxiv2md CLI 输出过短 ({len(content)} bytes)，改用 API")
                generated.unlink(missing_ok=True)
    except Exception as e:
        print(f"  ⚠️  arxiv2md CLI 失败 ({e})，改用 API")

    # ── Fallback: Python API ──
    try:
        from arxiv2md import ingest_paper_sync
        result = ingest_paper_sync(arxiv_id)
        import re as _re
        content = _re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', result.content)
        out_path.write_text(content, encoding="utf-8")
        # Write to cache
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")
        return content
    except ImportError:
        raise RuntimeError("arxiv2md not installed")
    except Exception as e:
        raise RuntimeError(f"arxiv2md API 也失败: {e}")


# ── Phase auto-runner (shared across scripts) ──


def run_phase_auto(phase2_args: list[str] | None = None):
    """Blocking phase1→auto-spawn→phase2 runner.
    
    Call this AFTER prepare_tasks() has written task files.
    1. Prints spawn instruction for the agent.
    2. Calls wait_for_tasks() to poll for .done markers.
    3. When all done, re-executes the script with --phase2.
    
    phase2_args: override sys.argv for phase2 re-execution (e.g. ['--phase2']).
                 Defaults to original args + '--phase2'.
    """
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = TASK_DIR / "manifest.json"
    if not manifest_path.exists():
        print("Error: no manifest.json found. Run --phase1 first.")
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    task_ids = [t["id"] for t in manifest["tasks"]]
    if not task_ids:
        print("No tasks to process.")
        return

    print(f"\n{'='*60}")
    print(f"📋 {len(task_ids)} task(s) ready. Spawn subagents now.")
    for t in manifest["tasks"]:
        print(f"  → {t['id']}")
    print(f"{'='*60}\n")

    # Poll until all tasks complete
    print(f"⏳ Waiting for {len(task_ids)} subagent(s) to complete...")
    if wait_for_tasks(task_ids, timeout=900, poll=10):
        print(f"✅ All tasks completed. Re-running with --phase2...")
        import subprocess, sys
        args = phase2_args if phase2_args is not None else sys.argv + ["--phase2"]
        subprocess.run([sys.executable] + args)
    else:
        print(f"⚠️  Timeout waiting for tasks: {task_ids}")
        print(f"   Once done, re-run with --phase2")
