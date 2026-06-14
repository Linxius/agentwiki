#!/usr/bin/env python3
"""
Pipeline status check — no LLM calls, deterministic.

Usage:
    python tools/status.py                    # print report
    python tools/status.py --json             # machine-readable JSON
    python tools/status.py --blockers         # show what blocks each step
    python tools/status.py --next filter      # check if 'filter' can run
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from _utils import read_file

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX_MD = REPO_ROOT / "raw" / "inbox" / "inbox.md"
INBOX_DIR = REPO_ROOT / "raw" / "inbox"
DIGEST_DIR = REPO_ROOT / "raw" / "digest"
BRIEF_FILE = DIGEST_DIR / "brief.md"
CONFIG_FILE = REPO_ROOT / "config.json"
STATE_FILE = REPO_ROOT / "raw" / ".feeds-state.json"

# Pipeline order: each step's prerequisites
PIPELINE_STEPS = [
    ("inbox", "解析 inbox.md 链接", []),
    ("feeds", "拉取 feeds", []),
    ("filter", "筛选 inbox/", ["inbox_files", "inbox_links"]),
    ("deep-read", "生成深度阅读", ["brief_with_checked_deepread"]),
    ("ingest-from-digest", "合入 wiki", ["brief_with_checked_ingest"]),
]


def check_inbox_links():
    """Count markdown links in inbox.md."""
    content = read_file(INBOX_MD)
    links = re.findall(r'^\s*[-*]\s+https?://\S+', content, re.MULTILINE)
    links += re.findall(r'^\s*[-*]\s+\d{4}\.\d{4,5}', content, re.MULTILINE)
    return len(links)


def check_inbox_files():
    """Count .md files in inbox/ subdirectories."""
    if not INBOX_DIR.exists():
        return 0
    count = 0
    for p in INBOX_DIR.iterdir():
        if p.is_dir():
            count += len([f for f in p.glob("*.md")])
        elif p.suffix == ".md" and p.name != "inbox.md":
            count += 1
    return count


def check_brief():
    """Return status info about brief.md."""
    content = read_file(BRIEF_FILE)
    if not content:
        return {"exists": False, "has_content": False, "deep_read": 0, "ingest": 0}

    deep_read = len(re.findall(r'\[x\]\s*深度阅读|\[X\]\s*深度阅读', content))
    ingest = len(re.findall(r'\[x\]\s*合入 wiki|\[X\]\s*合入 wiki', content))

    return {
        "exists": True,
        "has_content": bool(content.strip()),
        "deep_read": deep_read,
        "ingest": ingest,
    }


def check_feeds():
    """Check feed sources and last fetch dates."""
    config = json.loads(read_file(CONFIG_FILE)) if CONFIG_FILE.exists() else {}
    sources = config.get("feeds", {}).get("sources", [])

    state = json.loads(read_file(STATE_FILE)) if STATE_FILE.exists() else {}

    results = []
    for s in sources:
        name = s.get("name", "?")
        enabled = s.get("enabled", True)
        source_state = state.get(name, {})
        last_fetch = source_state.get("last_fetch_date")

        results.append({
            "name": name,
            "enabled": enabled,
            "last_fetch_date": last_fetch,
        })

    return results


TRIGGER_WORDS = {
    "处理 inbox 链接": "inbox",
    "filter 筛选": "filter",
    "生成深度阅读": "deep read",
    "合入 wiki": "ingest from digest",
    "拉取 feeds": "feeds",
    "拉取 feeds（首次）": "feeds",
}


def suggest_next(brief, inbox_links, inbox_files, feeds):
    """Suggest next pipeline step with trigger words."""
    steps = []

    if inbox_links > 0:
        steps.append("处理 inbox 链接")

    if inbox_files > 0:
        steps.append("filter 筛选")

    if brief["deep_read"] > 0 and brief["deep_read"] > 0:
        steps.append("生成深度阅读")

    if brief["ingest"] > 0:
        steps.append("合入 wiki")

    now = datetime.now(timezone.utc)
    for f in feeds:
        if f["enabled"] and f["last_fetch_date"]:
            last = datetime.strptime(f["last_fetch_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_since = (now - last).days
            if days_since >= 1:
                steps.append("拉取 feeds")
                break
        elif f["enabled"] and not f["last_fetch_date"]:
            steps.append("拉取 feeds（首次）")
            break

    if not steps:
        return "无待办事项"

    steps = list(dict.fromkeys(steps))
    return " → ".join(f"{s}（触发词: {TRIGGER_WORDS[s]}）" for s in steps)


def run_status():
    inbox_links = check_inbox_links()
    inbox_files = check_inbox_files()
    brief = check_brief()
    feeds = check_feeds()
    suggestion = suggest_next(brief, inbox_links, inbox_files, feeds)

    return {
        "inbox_links": inbox_links,
        "inbox_files": inbox_files,
        "brief": brief,
        "feeds": feeds,
        "suggestion": suggestion,
    }


def format_report(data):
    lines = ["📋 Pipeline Status:\n"]
    lines.append(f"1. inbox: {data['inbox_links']} links in inbox.md")
    lines.append(f"2. inbox: {data['inbox_files']} files pending filter")

    b = data["brief"]
    if b["exists"] and b["has_content"]:
        lines.append(f"3. brief: 简报已生成")
    elif b["exists"]:
        lines.append(f"3. brief: 简报为空")
    else:
        lines.append(f"3. brief: 未生成")

    lines.append(f"4. deep-read: {b['deep_read']} checked")
    lines.append(f"5. ingest: {b['ingest']} checked")

    for f in data["feeds"]:
        name = f["name"]
        if not f["enabled"]:
            lines.append(f"6. feeds: {name} (disabled)")
        elif f["last_fetch_date"]:
            now = datetime.now(timezone.utc)
            last = datetime.strptime(f["last_fetch_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days = (now - last).days
            lines.append(f"6. feeds: {name} last fetch {f['last_fetch_date']} ({days}d ago)")
        else:
            lines.append(f"6. feeds: {name} never fetched")

    lines.append(f"\n→ 建议: {data['suggestion']}")
    return "\n".join(lines)


# ── Blocker detection ────────────────────────────────────────────────

def check_blockers(data):
    """Check each pipeline step and identify blockers."""
    results = []
    inbox_files = data["inbox_files"]
    inbox_links = data["inbox_links"]
    brief = data["brief"]

    blockers = {
        "inbox_files": inbox_files > 0,
        "inbox_links": inbox_links > 0,
        "brief_with_checked_deepread": brief["exists"] and brief["deep_read"] > 0,
        "brief_with_checked_ingest": brief["exists"] and brief["ingest"] > 0,
    }

    for step_id, step_label, prereqs in PIPELINE_STEPS:
        missing = [p for p in prereqs if not blockers.get(p)]
        if missing:
            reasons = {
                "inbox_files": "inbox/ 中没有待筛选文件",
                "inbox_links": "inbox.md 中无链接",
                "brief_with_checked_deepread": "brief.md 不存在或未勾选深度阅读",
                "brief_with_checked_ingest": "brief.md 不存在或未勾选合入 wiki",
            }
            reasons_text = "；".join(reasons[p] for p in missing)
            results.append({"step": step_id, "label": step_label, "blocked": True, "reason": reasons_text})
        else:
            results.append({"step": step_id, "label": step_label, "blocked": False, "reason": ""})

    return results


def check_next_step(data, target):
    """Check if a specific step can run."""
    blockers = check_blockers(data)
    for b in blockers:
        if b["step"] == target:
            return b
    return {"step": target, "blocked": True, "reason": f"未知步骤: {target}"}


def format_blockers_report(blockers):
    lines = ["🔒 Pipeline Blockers:\n"]
    for b in blockers:
        if b["blocked"]:
            lines.append(f"✗ {b['label']} — 阻塞: {b['reason']}")
        else:
            lines.append(f"✓ {b['label']} — 可以执行")
    return "\n".join(lines)


if __name__ == "__main__":
    data = run_status()

    if "--blockers" in sys.argv:
        blockers = check_blockers(data)
        print(format_blockers_report(blockers))

    elif "--next" in sys.argv:
        idx = sys.argv.index("--next")
        if idx + 1 < len(sys.argv):
            target = sys.argv[idx + 1]
            result = check_next_step(data, target)
            if result["blocked"]:
                print(f"✗ {result['label']}: {result['reason']}")
                sys.exit(1)
            else:
                print(f"✓ {result['label']} — 可以执行")
        else:
            print("用法: python tools/status.py --next <step>")
            print(f"步骤: {', '.join(s[0] for s in PIPELINE_STEPS)}")
            sys.exit(1)

    elif "--json" in sys.argv:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    else:
        print(format_report(data))
