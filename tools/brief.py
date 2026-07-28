#!/usr/bin/env python3
"""
Brief lifecycle management — archive completed entries by source date.

Entry is terminal (can be archived) when:
  - [x] 已合入  (imported to wiki)
  - [x] 不感兴趣  (explicitly skipped)

Usage:
    python tools/brief.py                     # auto-archive all completed date groups
    python tools/brief.py status              # show processing status by date
    python tools/brief.py --date YYYY-MM-DD   # force-archive a specific date
"""

import re
import sys
from pathlib import Path
from datetime import date as _date

REPO_ROOT = Path(__file__).parent.parent
BRIEF_FILE = REPO_ROOT / "raw" / "digest" / "brief.md"
BRIEF_DIR = REPO_ROOT / "raw" / "digest" / "brief"
BRIEF_DIR.mkdir(parents=True, exist_ok=True)

HEADER_RE = re.compile(r'^#{3,4} (.+)')
SOURCE_PATH_RE = re.compile(r'- 源文件:\s*(.+)')
DATE_FROM_SOURCE_RE = re.compile(r'sources/(\d{4}-\d{2}-\d{2})/')


def parse_entries(content: str) -> list[dict]:
    """Parse brief.md into entry dicts with position and state."""
    lines = content.split('\n')
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = HEADER_RE.match(line)
        if m and not line.lstrip().startswith('### ['):
            entry_lines = []
            next_i = i + 1
            while next_i < len(lines):
                if HEADER_RE.match(lines[next_i]) and not lines[next_i].lstrip().startswith('### ['):
                    break
                entry_lines.append(lines[next_i])
                next_i += 1
            et = '\n'.join(entry_lines)

            src_path = ''
            sp = SOURCE_PATH_RE.search(et)
            if sp:
                src_path = sp.group(1).strip()

            entry_date = ''
            dm = DATE_FROM_SOURCE_RE.search(src_path)
            if dm:
                entry_date = dm.group(1)

            entries.append({
                'start': i,
                'end': next_i,
                'title': m.group(1).strip(),
                'date': entry_date,
                'source_path': src_path,
                'is_ingested': bool(re.search(r'\[x\]\s*已合入|\[X\]\s*已合入', et)),
                'is_disinterested': bool(re.search(r'\[x\]\s*不感兴趣|\[X\]\s*不感兴趣', et)),
            })
            i = next_i
        else:
            i += 1
    return entries


def group_by_date(entries: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for e in entries:
        d = e['date'] or '_nodate'
        groups.setdefault(d, []).append(e)
    return groups


def is_terminal(e: dict) -> bool:
    return e['is_ingested'] or e['is_disinterested']


def mark_entry_done(content: str, title: str, checkbox_type: str) -> str:
    """In brief content, change '[x] <type>' to '[x] 已<type>' for entry matching title.
    checkbox_type: '深度阅读' or '合入 wiki'.
    Returns updated content (unchanged if no match).
    """
    old = rf'\[x\]\s*{re.escape(checkbox_type)}\s*|\[X\]\s*{re.escape(checkbox_type)}\s*'
    new = f'[x] 已{checkbox_type}'

    lines = content.split('\n')
    in_target = False

    for i, line in enumerate(lines):
        # Detect entry boundary by #### or ### header
        if re.match(r'^#{3,4}\s+', line):
            if title in line:
                in_target = True
            elif not line.lstrip().startswith('### ['):
                in_target = False
        elif re.match(r'^##\s', line):
            in_target = False

        if in_target and re.search(old, line):
            lines[i] = re.sub(old, new, line)
            break

    return '\n'.join(lines)


def _empty_brief(today: str = '') -> str:
    t = today or _date.today().isoformat()
    return f"""# 资讯简报  {t}

---

## 今日暂无待处理资讯

---

## 操作指引

- 勾选「深度阅读」后，告诉 agent 生成详细解读
- 勾选「合入 wiki」后，告诉 agent 执行合入
- 勾选「不感兴趣」后，运行 deep-read 自动生成兴趣列表更新建议
"""


def run_archive(force_date: str = None) -> list[str]:
    """Archive completed entries by date. Returns list of archived date strings."""
    if not BRIEF_FILE.exists():
        print("brief.md not found.")
        return []

    content = BRIEF_FILE.read_text(encoding='utf-8')
    if not content.strip():
        return []

    entries = parse_entries(content)
    if not entries:
        return []

    groups = group_by_date(entries)

    # Separate terminal vs keep
    to_archive: dict[str, list[dict]] = {}
    keep: list[dict] = []

    for d, group in groups.items():
        if d == '_nodate':
            keep.extend(group)
            continue
        all_done = all(is_terminal(e) for e in group)
        forced = force_date == d
        if all_done or forced:
            to_archive[d] = group
        else:
            keep.extend(group)

    if not to_archive:
        print("  No completed date groups to archive.")
        return []

    lines = content.split('\n')

    # Build archive files
    archived_dates = []
    for d in sorted(to_archive):
        group = to_archive[d]
        # Collect entry text in order
        parts = []
        for e in group:
            chunk = '\n'.join(lines[e['start']:e['end']])
            parts.append(chunk)
        archive_body = '\n\n'.join(parts)

        archive_path = BRIEF_DIR / f"{d}.md"
        if archive_path.exists():
            existing = archive_path.read_text(encoding='utf-8')
            combined = existing.rstrip() + '\n\n---\n\n' + archive_body + '\n'
        else:
            combined = archive_body + '\n'
        archive_path.write_text(combined, encoding='utf-8')
        print(f"  📦 brief/{d}.md  ← {len(group)} entries")
        archived_dates.append(d)

    # Rebuild brief.md with preamble + kept entries
    first_entry = min((e['start'] for e in entries), default=0)
    preamble = lines[:first_entry]

    new_lines = list(preamble)
    for e in keep:
        new_lines.extend(lines[e['start']:e['end']])

    # Clean up consecutive blanks
    new_content = '\n'.join(new_lines)
    new_content = re.sub(r'\n{3,}', '\n\n', new_content).strip()

    if not keep:
        # Extract header date from existing content
        hd = re.search(r'# 资讯简报\s+(\d{4}-\d{2}-\d{2})', content)
        today = hd.group(1) if hd else _date.today().isoformat()
        new_content = _empty_brief(today)

    BRIEF_FILE.write_text(new_content + '\n', encoding='utf-8')
    print(f"  🧹 brief.md updated ({len(keep)} entries remaining)")

    return archived_dates


def show_status():
    """Print processing status grouped by date."""
    if not BRIEF_FILE.exists():
        print("brief.md not found.")
        return

    content = BRIEF_FILE.read_text(encoding='utf-8')
    if not content.strip():
        print("brief.md is empty.")
        return

    entries = parse_entries(content)
    if not entries:
        print("brief.md has no entry items.")
        return

    groups = group_by_date(entries)

    print("📋 Brief 处理状态\n")
    for d in sorted(groups):
        group = groups[d]
        if d == '_nodate':
            label = "未归类"
        else:
            label = d
        total = len(group)
        terminal = sum(1 for e in group if is_terminal(e))
        ingested = sum(1 for e in group if e['is_ingested'])
        skipped = sum(1 for e in group if e['is_disinterested'])
        pending = total - terminal

        status = "✅ 可归档" if pending == 0 else f"⏳ {pending}/{total} 待处理"
        print(f"  {label}: {status}  ({ingested} 已合入, {skipped} 不感兴趣, {pending} 待处理)")

    print()


if __name__ == '__main__':
    if '--date' in sys.argv:
        idx = sys.argv.index('--date')
        if idx + 1 < len(sys.argv):
            force = sys.argv[idx + 1]
            run_archive(force_date=force)
        else:
            print("Usage: python tools/brief.py [--date YYYY-MM-DD]")
            sys.exit(1)
    elif 'status' in sys.argv:
        show_status()
    else:
        run_archive()
