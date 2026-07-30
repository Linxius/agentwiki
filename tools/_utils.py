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


PROMPT_FILE = REPO_ROOT / "raw" / ".tmp" / "wiki-llm-prompt.md"
RESPONSE_FILE = REPO_ROOT / "raw" / ".tmp" / "wiki-llm-response.md"


def call_llm(prompt, max_tokens=8192, task_id=None):
    """调用 LLM，支持三种模式。

    模式 1 — task 文件模式（默认）：
        写 prompt 到 TASK_DIR，返回 ""。agent 处理 task 文件后执行 --phase2。
        当 `task_id` 参数指定时使用该 ID，否则自动生成。

    模式 2 — 直接 LLM 模式（WIKI_LLM_DIRECT=1）：
        写 prompt 到 PROMPT_FILE，打印说明后返回 ""。
        agent 处理 prompt，将结果写入 RESPONSE_FILE，重新运行命令即可读取。

    模式 3 — 恢复模式（已存在 RESPONSE_FILE）：
        读取 RESPONSE_FILE 内容并清空文件，返回内容字符串。
    """
    # 模式 3: 检查是否有已写入的响应
    if RESPONSE_FILE.exists():
        content = RESPONSE_FILE.read_text(encoding="utf-8")
        RESPONSE_FILE.unlink(missing_ok=True)
        if content.strip():
            return content
        # 空文件 → 继续走正常流程

    if os.environ.get("WIKI_LLM_DIRECT") == "1":
        # 模式 2: 写 prompt 到单文件
        PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROMPT_FILE.write_text(prompt, encoding="utf-8")
        print(f"\n{'='*60}")
        print(f"📋 Prompt 已写入: {PROMPT_FILE}")
        print(f"   处理步骤：")
        print(f"   1. 读取 {PROMPT_FILE}")
        print(f"   2. 处理请求并将结果写入 {RESPONSE_FILE}")
        print(f"   3. 重新运行相同命令（会自动读取响应）")
        print(f"{'='*60}\n")
        return ""

    # 模式 1: task 文件模式
    tid = task_id if task_id else f"auto_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
    prepare_task(tid, prompt, max_tokens)
    print(f"  📝 Task 已写入: {TASK_DIR / tid}.json")
    return ""


def auto_call_or_phase1(prompt: str, max_tokens: int = 8192, task_id: str = "auto") -> str:
    import hashlib
    if '--phase2' in sys.argv:
        return read_result(task_id)
    tid = task_id if task_id != "auto" else f"auto_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
    call_llm(prompt, max_tokens, task_id=tid)
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
    """Clean up task and result directories (including .done markers and shared context).
    
    Only cleans when --clean is in sys.argv, or when called explicitly with force=True.
    """
    if "--clean" not in sys.argv:
        return  # always safe — opt-in
    import shutil
    if TASK_DIR.exists():
        shutil.rmtree(TASK_DIR, ignore_errors=True)
    if RESULT_DIR.exists():
        shutil.rmtree(RESULT_DIR, ignore_errors=True)
    # Clean shared context cache
    tmp_dir = REPO_ROOT / "raw" / ".tmp"
    for f in tmp_dir.glob("wiki-ingest-context*"):
        f.unlink(missing_ok=True)


def load_manifest() -> dict | None:
    """Load manifest.json, return None if not found."""
    manifest_path = TASK_DIR / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def list_all_tasks() -> list[dict]:
    """Return all tasks from manifest.json, or empty list."""
    manifest = load_manifest()
    if not manifest:
        return []
    return manifest.get("tasks", [])


def list_pending_tasks() -> list[dict]:
    """Return tasks without .done markers (not yet completed)."""
    if not RESULT_DIR.exists():
        return list_all_tasks()
    pending = []
    for t in list_all_tasks():
        tid = t["id"]
        if not (RESULT_DIR / f"{tid}.done").exists():
            pending.append(t)
    return pending


def list_failed_tasks() -> list[dict]:
    """Return tasks with .done marker but empty result (subagent failed)."""
    if not RESULT_DIR.exists():
        return []
    failed = []
    for t in list_all_tasks():
        tid = t["id"]
        done = RESULT_DIR / f"{tid}.done"
        if done.exists():
            result_content = read_result(tid)
            if not result_content.strip():
                failed.append(t)
    return failed


def retry_failed_tasks() -> int:
    """Re-queue failed tasks by removing their .done markers.
    Returns count of re-queued tasks.
    """
    if not RESULT_DIR.exists():
        return 0
    count = 0
    for t in list_all_tasks():
        tid = t["id"]
        done = RESULT_DIR / f"{tid}.done"
        if done.exists():
            result_content = read_result(tid)
            if not result_content.strip():
                done.unlink(missing_ok=True)
                # Also remove any stale result file
                for ext in (".txt", ".json"):
                    rf = RESULT_DIR / f"{tid}{ext}"
                    rf.unlink(missing_ok=True)
                count += 1
                print(f"  🔄 重排队: {tid}")
    return count


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


def _extract_arxiv_id_from_content(content: str) -> str | None:
    """Extract arxiv ID from YAML frontmatter url field or content body."""
    # Frontmatter: url: "https://arxiv.org/abs/2503.10637"
    m = re.search(r'^url:\s*["\']?https?://arxiv\.org/abs/(\d{4}\.\d{4,5})', content, re.MULTILINE)
    if m:
        return m.group(1)
    # Plain text: arXiv:2503.10637
    m = re.search(r'[Aa][Rr][Xx][Ii][Vv]:\s*(\d{4}\.\d{4,5})', content)
    if m:
        return m.group(1)
    # Pattern in body: 2503.10637
    m = re.search(r'(\d{4}\.\d{4,5})', content[:2000])
    if m:
        return m.group(1)
    return None


def _ensure_title_header(content: str) -> str:
    """If content starts with ## or --- (not # Title), extract title and add # line."""
    if re.match(r'^#\s+', content):
        return content  # already has H1 title
    # Try frontmatter title
    fm = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm:
        title_m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', fm.group(1), re.MULTILINE)
        if title_m:
            title = title_m.group(1).strip().strip('"').strip("'")
            rest = content[fm.end():]
            return f"# {title}\n\n{rest}"
    # Try first heading (## Abstract → promote)
    h2 = re.search(r'^##\s+(.+)$', content, re.MULTILINE)
    if h2:
        title = h2.group(1).strip()
        if len(title) < 100:
            return f"# {title}\n\n{content}"
    return content


def safe_download_arxiv(arxiv_id: str, out_path: Path) -> str:
    """Download arXiv paper via arxiv2md CLI, handling the -o directory quirk.
    
    arxiv2md's -o flag creates a DIRECTORY with the given name and puts the
    actual file inside as <Title>.md. This wrapper: passes a directory to -o,
    globs for the output file, validates content length (≥5000), ensures # Title
    header exists, and renames to out_path. Falls back to Python API on CLI failure.
    
    Caches results in raw/.tmp/arxiv-cache/<arxiv_id>/<arxiv_id>.md.
    Cache includes arxiv_id fingerprint for content validation.
    
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
    MIN_CACHE_SIZE = 5000
    if cache_path.exists() and cache_path.stat().st_size >= MIN_CACHE_SIZE:
        content = cache_path.read_text(encoding="utf-8")
        # Validate cache content matches expected arxiv_id
        cached_id = _extract_arxiv_id_from_content(content)
        if cached_id and cached_id != arxiv_id:
            print(f"  ⚠️  缓存内容不匹配：期望 arxiv:{arxiv_id}，实际 {cached_id}，重新下载")
            cache_path.unlink(missing_ok=True)
        else:
            out_path.write_text(content, encoding="utf-8")
            print(f"  📦 使用缓存: {cache_path}")
            return content
    elif cache_path.exists():
        print(f"  ⚠️  缓存文件过小 ({cache_path.stat().st_size} bytes)，重新下载")
        cache_path.unlink(missing_ok=True)

    # ── CLI mode: arxiv2md <id> -o <dir> → outputs to <dir>/<Title>.md ──
    # Record existing .md files before CLI to detect leftovers
    existing_before = set(out_dir.glob("*.md")) if out_dir.exists() else set()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "arxiv2md", arxiv_id,
             "--frontmatter", "--remove-toc",
             "-o", str(out_dir)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            new_files = [f for f in out_dir.glob("*.md") if f not in existing_before]
            if new_files:
                generated = max(new_files, key=lambda f: f.stat().st_mtime)
                content = generated.read_text(encoding="utf-8")
                if len(content) >= 5000:
                    content = _ensure_title_header(content)
                    if generated != out_path:
                        # Handle Windows "file exists" error
                        if out_path.exists():
                            out_path.unlink()
                        generated.rename(out_path)
                    out_path.write_text(content, encoding="utf-8")
                    # Validate arxiv_id in content; reject on mismatch
                    actual_id = _extract_arxiv_id_from_content(content)
                    if actual_id and actual_id != arxiv_id:
                        print(f"  ⚠️  arxiv ID 不匹配：期望 {arxiv_id}，实际 {actual_id}，走下一个回退")
                        out_path.unlink(missing_ok=True)
                        generated.unlink(missing_ok=True)
                    else:
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        cache_path.write_text(content, encoding="utf-8")
                        return content
                print(f"  ⚠️  arxiv2md CLI 输出过短 ({len(content)} bytes)，改用 API")
                generated.unlink(missing_ok=True)
    except Exception as e:
        print(f"  ⚠️  arxiv2md CLI 失败 ({e})，改用 API")
    # Clean up CLI-created temp files (title-named .md) before fallback
    for f in list(out_dir.glob("*.md")):
        if f not in existing_before and f != out_path:
            f.unlink(missing_ok=True)

    # ── Fallback: Python API ──
    try:
        from arxiv2md import ingest_paper_sync
        result = ingest_paper_sync(arxiv_id)
        import re as _re
        content = _re.sub(r'(arxiv\.org)/html//html/', r'\1/html/', result.content)
        content = _ensure_title_header(content)
        out_path.write_text(content, encoding="utf-8")
        if len(content) >= 5000:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(content, encoding="utf-8")
            return content
        print(f"  ⚠️  arxiv2md API 输出过短 ({len(content)} bytes)")
    except ImportError:
        pass  # fall through to marker below
    except Exception as e:
        print(f"  ⚠️  arxiv2md API 失败 ({e})")

    # ── arxiv2md 均失败 → 写 agent_action 标记，由 agent 通过 MCP 补全 ──
    marker = f"""---
url: https://arxiv.org/abs/{arxiv_id}
source: ""
agent_action: fetch_alphaxiv
agent_note: "arxiv2md CLI/API 均失败，需要 agent 通过 alphaXiv HTTP overview 获取，否则 MCP fullText"
---

"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(marker, encoding="utf-8")
    raise RuntimeError(f"arxiv2md CLI/API 均失败，写入 agent_action 标记待 MCP 补全")


def fetch_web_source(url: str, out_path: Path) -> bool:
    """Fetch a non-arxiv web page and save as markdown source file.

    Priority: trafilatura (best) -> markitdown HTML->MD -> raw text.
    Returns True on success.
    """
    import requests as _req
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; WikiBot/1.0)'}
        resp = _req.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        # 1) trafilatura - clean article extraction
        try:
            import trafilatura
            text = trafilatura.extract(resp.text, include_formatting=True, include_links=True)
            if text and len(text) > 200:
                out_path.write_text(text, encoding="utf-8")
                return True
        except ImportError:
            pass

        # 2) markitdown - HTML->MD conversion
        try:
            from markitdown import MarkItDown
            import tempfile, os as _os
            tmp = tempfile.NamedTemporaryFile(suffix='.html', delete=False)
            tmp.write(resp.content)
            tmp.close()
            md = MarkItDown(enable_plugins=False)
            result = md.convert(tmp.name)
            _os.unlink(tmp.name)
            if result and result.text_content and len(result.text_content) > 200:
                out_path.write_text(result.text_content, encoding="utf-8")
                return True
        except Exception:
            pass

        # 3) fallback: URL + first 10K chars
        out_path.write_text(f"# {url}\n\nURL: {url}\n\n{resp.text[:10000]}", encoding="utf-8")
        return bool(resp.text)
    except Exception as e:
        print(f"  Warning: web fetch failed for {url}: {e}")
        return False


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
    print(f"📋 {len(task_ids)} task(s) ready. Agent 请处理：")
    for t in manifest["tasks"]:
        print(f"  → {t['id']}")
    print(f"\n选项：")
    print(f"  a) 处理 task 后执行 --phase2")
    print(f"  b) --retry-failed 重试空结果 task")
    print(f"  c) --clean 清除所有 task 文件")
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
