#!/usr/bin/env python3
"""Translate figure captions in brief.md from English to Chinese.
Usage: python tools/_translate_captions.py

Extracts all **caption** lines from brief.md, sends them as a batch
to a subagent for translation, then updates the brief in place.
"""
import json, re, sys, subprocess, tempfile, os
from pathlib import Path

REPO = Path(__file__).parent.parent
TASK_DIR = REPO / "raw" / ".tmp" / "wiki-tasks"
BRIEF = REPO / "raw/digest/brief.md"

def extract_captions(text: str) -> list[dict]:
    """Find all **caption** lines that precede a ![](url) line."""
    captions = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        m = re.match(r'^\*\*(.+)\*\*$', line.strip())
        if m and i + 1 < len(lines) and lines[i+1].strip().startswith("!["):
            captions.append({"index": i, "original": m.group(1), "translated": ""})
    return captions

def main():
    if not BRIEF.exists():
        print(f"❌ {BRIEF} not found")
        sys.exit(1)

    content = BRIEF.read_text(encoding="utf-8")
    captions = extract_captions(content)

    if not captions:
        print("No captions found to translate.")
        return

    # Build batch translation prompt
    lines_to_translate = "\n".join(
        f"{i+1}. {c['original']}"
        for i, c in enumerate(captions)
    )

    prompt = f"""将以下科研论文图片标题从英文翻译为中文。保持技术术语准确，翻译简洁通顺。
每行对应翻译，保持行号对应。

原文:
{lines_to_translate}

返回格式：直接输出翻译文本，每行一条，保持行号对应。不要序号，不要代码块。"""

    print(f"📤 Sending {len(captions)} captions for batch translation...")

    # Write prompt to temp file for subagent
    task_file = TASK_DIR / "translate-captions.json"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(json.dumps({
        "id": "translate-captions",
        "prompt": prompt,
        "max_tokens": 4096,
    }, ensure_ascii=False), encoding="utf-8")

    print(f"Task written to {task_file}")
    print(f"\nRun filter in agent to process:\n  actor run general 'Translate captions' '...'")
    print(f"\nThen run this script again with --apply <translations.txt>")

if __name__ == "__main__":
    apply = False
    trans_file = None
    for arg in sys.argv[1:]:
        if arg == "--apply" and len(sys.argv) > sys.argv.index(arg) + 1:
            apply = True
            trans_file = sys.argv[sys.argv.index(arg) + 1]
        elif arg == "--help":
            print(__doc__)
            sys.exit(0)

    if apply and trans_file:
        if not Path(trans_file).exists():
            print(f"❌ Translation file not found: {trans_file}")
            sys.exit(1)
        translations = Path(trans_file).read_text(encoding="utf-8").strip().split("\n")
        content = BRIEF.read_text(encoding="utf-8")
        captions = extract_captions(content)

        if len(translations) != len(captions):
            print(f"⚠️  Mismatch: {len(translations)} translations vs {len(captions)} captions")
            sys.exit(1)

        lines = content.split("\n")
        for i, (cap, trans) in enumerate(zip(captions, translations)):
            trans = trans.strip().strip('"').strip("'")
            old = f"**{cap['original']}**"
            new = f"**{trans}**"
            lines[cap['index']] = new

        BRIEF.write_text("\n".join(lines), encoding="utf-8")
        print(f"✅ Translated {len(captions)} captions in {BRIEF}")
    else:
        main()
