#!/usr/bin/env python3
"""
Graph Self-Healing Tool

Automatically retrieves "Missing Entity Pages" from the wiki and generates
comprehensive definition pages for them using the LLM.
It resolves broken entity links by scanning existing contexts where the entity is referenced.

Usage:
    python tools/heal.py              # main mode (direct LLM)
    python tools/heal.py --phase1     # write prompts for subagent processing
    python tools/heal.py --phase2     # read results from subagent processing
"""

import argparse
import sys
from pathlib import Path

# Ensure tools can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from _utils import call_llm, prepare_tasks, read_results, clean_task_dirs
from tools.lint import find_missing_entities, all_wiki_pages

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
ENTITIES_DIR = WIKI_DIR / "entities"


def search_sources(entity: str, pages: list[Path]) -> list[Path]:
    """Find up to 15 pages where this entity is mentioned natively."""
    sources = []
    for p in pages:
        if "entities" not in str(p.parent) and "concepts" not in str(p.parent):
            content = p.read_text(encoding="utf-8")
            if entity.lower() in content.lower():
                sources.append(p)
    return sources[:15]


def build_entity_prompt(entity: str, sources: list[Path]) -> str:
    """Build the LLM prompt for generating an entity definition page."""
    context = ""
    for s in sources:
        context += f"\n\n### {s.name}\n{s.read_text(encoding='utf-8')[:800]}"

    return f"""You are filling a data gap in the Personal LLM Wiki.
Create an Entity definition page for "{entity}".

Here is how the entity appears in the current sources:
{context}

Format:
---
title: "{entity}"
type: entity
tags: []
sources: {[s.name for s in sources]}
---

# {entity}

Write a comprehensive paragraph defining what `{entity}` means in the context of this wiki, its main significance, and any actions or associations related to it.
"""


def heal_missing_entities(phase1: bool = False, phase2: bool = False):
    pages = all_wiki_pages()
    missing_entities = find_missing_entities(pages)

    if not missing_entities:
        print("Graph is fully connected. No missing entities found!")
        return

    ENTITIES_DIR.mkdir(exist_ok=True, parents=True)
    print(f"Found {len(missing_entities)} missing entity nodes. Commencing auto-heal...")

    # Collect all (entity, sources) pairs
    tasks = []
    for entity in missing_entities:
        sources = search_sources(entity, pages)
        tasks.append((entity, sources))

    # ── Phase 1: write prompts to files for subagent processing ──
    if phase1:
        task_list = []
        for entity, sources in tasks:
            prompt = build_entity_prompt(entity, sources)
            task_list.append({
                "id": entity,
                "prompt": prompt,
                "max_tokens": 1500,
                "metadata": {"entity": entity},
            })
        prepare_tasks(task_list)
        return

    # ── Phase 2: read results from subagent processing ──
    if phase2:
        results_map = read_results()
        print(f"Reading {len(results_map)} results")
        saved = 0
        for entity, sources in tasks:
            raw = results_map.get(entity, "")
            if not raw:
                print(f"  No result for {entity}")
                continue
            out_path = ENTITIES_DIR / f"{entity}.md"
            out_path.write_text(raw, encoding="utf-8")
            print(f"  -> Saved {out_path.relative_to(REPO_ROOT)}")
            saved += 1
        clean_task_dirs()
        print(f"Done: {saved}/{len(tasks)} entity pages generated.")
        return

    # ── Default mode: direct LLM calls ──
    for entity, sources in tasks:
        print(f"Healing entity page for: {entity}")
        prompt = build_entity_prompt(entity, sources)
        try:
            result = call_llm(prompt, max_tokens=1500)
            out_path = ENTITIES_DIR / f"{entity}.md"
            out_path.write_text(result, encoding="utf-8")
            print(f" -> Saved to {out_path.relative_to(REPO_ROOT)}")
        except Exception as e:
            print(f" [!] Failed to generate {entity}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-heal missing entity pages in wiki")
    parser.add_argument("--phase1", action="store_true",
                        help="Write prompts to files for subagent processing")
    parser.add_argument("--phase2", action="store_true",
                        help="Read results from subagent processing")
    args = parser.parse_args()

    heal_missing_entities(phase1=args.phase1, phase2=args.phase2)
