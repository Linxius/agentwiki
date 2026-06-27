#!/usr/bin/env python3
"""
Code reading tool — collect source files and generate wiki pages.

Subcommands:
    collect   Scan a path (or clone a git repo) and output source code to stdout/file.
    write     Take analysis JSON and write a wiki page + update index/log.

Usage:
    python tools/code-read.py collect <path>                 # local file/dir
    python tools/code-read.py collect <git-url>              # auto-clone
    python tools/code-read.py collect <path> --url <git-url> # clone if missing
    python tools/code-read.py collect <path> -o /tmp/code.txt
    python tools/code-read.py write --json-file /tmp/analysis.json
    echo '{"title":"..."}' | python tools/code-read.py write --stdin
"""

import sys
import re
import json
import subprocess
import argparse
from pathlib import Path
from datetime import date

from _utils import read_file, write_file

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
CODES_DIR = REPO_ROOT / "raw" / "codes"
LOG_FILE = WIKI_DIR / "log.md"
INDEX_FILE = WIKI_DIR / "index.md"

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".r", ".m", ".mm", ".sh", ".bash", ".zsh",
    ".sql", ".html", ".css", ".scss", ".less", ".vue", ".svelte",
}

MAX_SOURCE_CHARS = 40000
KEEP_HEAD = 30000
KEEP_TAIL = 10000

GIT_URL_PATTERN = re.compile(
    r"^(https?://.*\.git"
    r"|git@[\w.-]+:.*\.git"
    r"|https?://github\.com/[\w.-]+/[\w.-]+"
    r"|https?://gitlab\.com/[\w.-]+/[\w.-]+"
    r"|https?://bitbucket\.org/[\w.-]+/[\w.-]+"
    r"|git@[\w.-]+:[\w.-]+/[\w.-]+)"
)


# ─── Git helpers ────────────────────────────────────────────────────

def is_git_url(text: str) -> bool:
    return bool(GIT_URL_PATTERN.match(text.strip()))


def repo_name_from_url(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    name = re.sub(r"\.git$", "", name)
    name = re.sub(r"[^\w.-]", "-", name)
    return name.lower()


def get_git_remote(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        url = result.stdout.strip()
        if url:
            return url
    return ""


def clone_repo(url: str, dest: Path = None) -> Path:
    if dest is None:
        name = repo_name_from_url(url)
        dest = CODES_DIR / name
    if dest.exists():
        print(f"目录已存在，跳过 clone: {dest}", file=sys.stderr)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"正在 clone: {url}", file=sys.stderr)
    print(f"目标: {dest}", file=sys.stderr)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"clone 失败:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("clone 完成", file=sys.stderr)
    return dest


# ─── Collect ────────────────────────────────────────────────────────

def collect_code_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        print(f"错误: 路径不存在 — {path}", file=sys.stderr)
        sys.exit(1)
    files = []
    for f in sorted(path.rglob("*")):
        if f.is_file() and f.suffix.lower() in CODE_EXTENSIONS:
            if ".git" in f.parts or "node_modules" in f.parts or "__pycache__" in f.parts:
                continue
            files.append(f)
    if not files:
        print(f"错误: 目录中未找到代码文件 — {path}", file=sys.stderr)
        sys.exit(1)
    return files


def read_source(files: list[Path]) -> str:
    parts = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = f.relative_to(REPO_ROOT) if f.is_relative_to(REPO_ROOT) else f
        parts.append(f"=== FILE: {rel} ===\n{content}")
    combined = "\n\n".join(parts)
    if len(combined) > MAX_SOURCE_CHARS:
        combined = combined[:KEEP_HEAD] + "\n\n... [截断] ...\n\n" + combined[-KEEP_TAIL:]
    return combined


def cmd_collect(args):
    """Collect code files and output to stdout or file."""
    urls = [a.strip() for a in args.paths if is_git_url(a.strip())]
    locals_ = [a.strip() for a in args.paths if not is_git_url(a.strip())]

    tasks = []
    for p in locals_:
        target = Path(p).resolve()
        if target.exists():
            source_url = args.url if args.url else get_git_remote(target)
            tasks.append((target, source_url))
        elif args.url:
            git_url = urls.pop(0) if urls else args.url
            target = clone_repo(git_url, target)
            tasks.append((target, git_url))
        elif urls:
            git_url = urls.pop(0)
            target = clone_repo(git_url, target)
            tasks.append((target, git_url))
        else:
            print(f"跳过: 路径不存在且无 git URL — {p}", file=sys.stderr)

    for u in urls:
        target = clone_repo(u)
        tasks.append((target, u))

    for target, source_url in tasks:
        print(f"处理: {target}", file=sys.stderr)
        files = collect_code_files(target)
        print(f"找到 {len(files)} 个代码文件", file=sys.stderr)

        source_text = read_source(files)
        print(f"源码总长度: {len(source_text)} 字符", file=sys.stderr)

        source_path = str(target.relative_to(REPO_ROOT)) if target.is_relative_to(REPO_ROOT) else str(target)

        result = {
            "source_path": source_path,
            "source_url": source_url,
            "file_count": len(files),
            "source_code": source_text,
        }

        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"已写入: {args.output}", file=sys.stderr)
        else:
            print(output)


# ─── Write ──────────────────────────────────────────────────────────

def build_wiki_page(data: dict, source_path: str, source_url: str = "") -> str:
    today = date.today().isoformat()
    title = data.get("title", "代码分析")
    language = data.get("language", "unknown")
    summary = data.get("summary", "")
    framework = data.get("framework_overview", "")
    algorithm = data.get("algorithm_flow", "")
    steps = data.get("step_breakdown", [])
    io_analysis = data.get("io_analysis", "")
    deps = data.get("dependencies", [])
    data_structures = data.get("key_data_structures", "")
    design_patterns = data.get("design_patterns", "")

    step_lines = []
    for s in steps:
        step_lines.append(
            f"**步骤 {s.get('step', '?')}: {s.get('name', '')}**\n"
            f"- 输入: {s.get('input', '')}\n"
            f"- 处理: {s.get('process', '')}\n"
            f"- 输出: {s.get('output', '')}"
        )
    steps_md = "\n\n".join(step_lines) if step_lines else "_（无步骤分解）_"

    deps_md = "\n".join(f"- {d}" for d in deps) if deps else "_（无外部依赖）_"

    mermaid_sections = []
    for key, label in [
        ("mermaid_architecture", "整体架构图"),
        ("mermaid_flowchart", "核心算法流程图"),
        ("mermaid_callgraph", "调用关系图"),
    ]:
        content = data.get(key, "").strip()
        if content and ("graph" in content or "flowchart" in content):
            mermaid_sections.append(f"### {label}\n\n{content}")
    mermaid_md = "\n\n".join(mermaid_sections) if mermaid_sections else "_（无流程图）_"

    url_line = f'url: {source_url}' if source_url else 'url: ""'
    page = f"""---
title: "{title}"
type: source
tags: [code, {language}]
date: {today}
source_file: {source_path}
{url_line}
language: {language}
---

## Summary
{summary}

## 原始出处
- 原始文件: [{source_path}]({source_path})
{"- 仓库地址: [" + source_url + "](" + source_url + ")" if source_url else ""}

## 框架概览
{framework}

## 核心算法流程
{algorithm}

## 步骤详解
{steps_md}

## 输入输出分析
{io_analysis}

## 流程图
{mermaid_md}

## 依赖关系
{deps_md}

## 关键数据结构
{data_structures}

## 设计模式
{design_patterns}

## Connections

## Contradictions
"""
    return page


def update_index(slug: str, title: str):
    content = read_file(INDEX_FILE)
    if not content:
        content = "# Wiki Index\n\n## Overview\n- [Overview](overview.md) — living synthesis\n\n## Sources\n\n## Entities\n\n## Concepts\n\n## Syntheses\n"
    new_entry = f"- [{title}](sources/{slug}.md) — 代码分析"
    section_header = "## Sources"
    lines = content.split("\n")
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip() == section_header:
            header_idx = i
            break
    if header_idx is None:
        content += f"\n{section_header}\n{new_entry}\n"
    else:
        insert_at = header_idx + 1
        while insert_at < len(lines) and lines[insert_at].strip() == "":
            insert_at += 1
        lines.insert(insert_at, new_entry)
        content = "\n".join(lines)
    write_file(INDEX_FILE, content)


def append_log(title: str):
    today = date.today().isoformat()
    entry = f"## [{today}] code-read | {title}"
    existing = read_file(LOG_FILE)
    write_file(LOG_FILE, entry.strip() + "\n\n" + existing)


def cmd_write(args):
    """Take analysis JSON and write wiki page."""
    if args.stdin:
        data = json.load(sys.stdin)
    elif args.json_file:
        data = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    else:
        print("错误: 需要 --json-file 或 --stdin", file=sys.stderr)
        sys.exit(1)

    slug = data.get("slug", "code-analysis")
    title = data.get("title", "代码分析")
    source_path = data.get("source_path", "")
    source_url = data.get("source_url", "")

    page = build_wiki_page(data, source_path, source_url)

    if args.dry_run:
        print(page)
        return

    out_path = WIKI_DIR / "sources" / f"{slug}.md"
    write_file(out_path, page)
    print(f"已写入: {out_path}", file=sys.stderr)

    update_index(slug, title)
    print(f"已更新 index.md", file=sys.stderr)

    append_log(title)
    print(f"已更新 log.md", file=sys.stderr)

    print(f"完成！标题: {title}", file=sys.stderr)


# ─── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="代码分析工具")
    sub = parser.add_subparsers(dest="command")

    p_collect = sub.add_parser("collect", help="收集代码文件并输出源码")
    p_collect.add_argument("paths", nargs="+", help="代码路径或 git URL")
    p_collect.add_argument("--url", help="git URL（用于 clone）")
    p_collect.add_argument("-o", "--output", help="输出文件路径（默认 stdout）")

    p_write = sub.add_parser("write", help="根据分析 JSON 生成 wiki 页面")
    p_write.add_argument("--json-file", help="分析 JSON 文件路径")
    p_write.add_argument("--stdin", action="store_true", help="从 stdin 读取 JSON")
    p_write.add_argument("--dry-run", action="store_true", help="仅预览不写入")

    args = parser.parse_args()
    if args.command == "collect":
        cmd_collect(args)
    elif args.command == "write":
        cmd_write(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
