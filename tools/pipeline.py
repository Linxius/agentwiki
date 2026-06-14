#!/usr/bin/env python3
"""
pipeline — run feeds → inbox → filter in sequence.

Usage:
    python tools/pipeline.py                  # full pipeline
    python tools/pipeline.py --no-feeds       # skip feeds pull
    python tools/pipeline.py --no-inbox       # skip inbox processing
    python tools/pipeline.py --no-filter      # skip filtering
    python tools/pipeline.py --dry-run        # show steps without running
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

STEPS = [
    ("feeds",  "tools/feeds.py",     "拉取 feeds"),
    ("inbox",  "tools/inbox.py",     "处理 inbox"),
    ("filter", "tools/filter.py",    "筛选分类"),
]


def run_step(name: str, script: str, label: str, dry_run: bool = False) -> bool:
    print(f"\n{'='*50}")
    print(f"  [{name}] {label}")
    print(f"{'='*50}")

    if dry_run:
        print(f"  (dry-run, would run: {script})")
        return True

    result = subprocess.run(
        [sys.executable, script],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"  ❌ [{name}] failed (exit code {result.returncode})")
        return False

    print(f"  ✅ [{name}] done")
    return True


def main():
    parser = argparse.ArgumentParser(description="Run feeds → inbox → filter pipeline")
    parser.add_argument("--no-feeds", action="store_true", help="Skip feeds pull")
    parser.add_argument("--no-inbox", action="store_true", help="Skip inbox processing")
    parser.add_argument("--no-filter", action="store_true", help="Skip filter")
    parser.add_argument("--dry-run", action="store_true", help="Show steps without running")
    args = parser.parse_args()

    skip = set()
    if args.no_feeds:
        skip.add("feeds")
    if args.no_inbox:
        skip.add("inbox")
    if args.no_filter:
        skip.add("filter")

    print("Pipeline: feeds → inbox → filter")
    if args.dry_run:
        print("Mode: dry-run\n")

    for name, script, label in STEPS:
        if name in skip:
            print(f"  ⏭️  [{name}] skipped")
            continue
        if not run_step(name, script, label, args.dry_run):
            print(f"\nPipeline aborted at [{name}]")
            sys.exit(1)

    print(f"\n{'='*50}")
    print("  ✅ Pipeline complete")
    print()


if __name__ == "__main__":
    main()
