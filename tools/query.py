#!/usr/bin/env python3
"""
Query the LLM Wiki.

Usage:
    python tools/query.py "What are the main themes across all sources?"
    python tools/query.py "How does ConceptA relate to ConceptB?" --save
    python tools/query.py "Summarize everything about EntityName" --save synthesis/my-analysis.md

Flags:
    --save              Save the answer back into the wiki (prompts for filename)
    --save <path>       Save to a specific wiki path
    --phase1            Write prompts to files for subagent processing
    --phase2            Read results from subagent processing
"""

import sys
import re
import json
import argparse
from pathlib import Path
from datetime import date

from _utils import read_file, write_file, call_llm, prepare_tasks, read_results, clean_task_dirs

REPO_ROOT = Path(__file__).parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
SCHEMA_FILE = REPO_ROOT / "AGENTS.md"


def find_relevant_pages(question: str, index_content: str) -> list[Path]:
    """Extract linked pages from index that seem relevant to the question.
    Uses character-level matching for CJK compatibility."""
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', index_content)
    question_lower = question.lower()
    relevant = []

    for title, href in md_links:
        title_lower = title.lower()
        # For CJK: check if any 2+ char substring of the title appears in question
        has_cjk = any('\u4e00' <= ch <= '\u9fff' for ch in title)
        if has_cjk:
            # Sliding window: check if any 2-char CJK bigram from title exists in question
            matched = any(
                title_lower[j:j+2] in question_lower
                for j in range(len(title_lower) - 1)
                if any('\u4e00' <= c <= '\u9fff' for c in title_lower[j:j+2])
            )
        else:
            # Latin: original word-based match (lowered threshold to >2)
            matched = any(word in question_lower for word in title_lower.split() if len(word) > 2)

        if matched:
            p = WIKI_DIR / href
            if p.exists() and p not in relevant:
                relevant.append(p)

    # Also try graph-based expansion: find neighbors of matched pages
    graph_json = REPO_ROOT / "graph" / "graph.json"
    if graph_json.exists() and relevant:
        try:
            graph_data = json.loads(graph_json.read_text(encoding="utf-8"))
            page_ids = {p.relative_to(WIKI_DIR).as_posix().replace('.md', '') for p in relevant}
            neighbors = set()
            for edge in graph_data.get('edges', []):
                if edge.get('confidence', 0) >= 0.7:
                    if edge['from'] in page_ids:
                        neighbors.add(edge['to'])
                    elif edge['to'] in page_ids:
                        neighbors.add(edge['from'])
            for nid in neighbors:
                np = WIKI_DIR / f"{nid}.md"
                if np.exists() and np not in relevant:
                    relevant.append(np)
        except (json.JSONDecodeError, KeyError):
            pass

    # Always include overview
    overview = WIKI_DIR / "overview.md"
    if overview.exists() and overview not in relevant:
        relevant.insert(0, overview)
    return relevant[:15]  # cap to avoid context overflow


def append_log(entry: str):
    existing = read_file(LOG_FILE)
    LOG_FILE.write_text(entry.strip() + "\n\n" + existing, encoding="utf-8")


def build_page_selection_prompt(question: str, index_content: str) -> str:
    return f"Given this wiki index:\n\n{index_content}\n\nWhich pages are most relevant to answering: \"{question}\"\n\nReturn ONLY a JSON array of relative file paths (as listed in the index), e.g. [\"sources/foo.md\", \"concepts/Bar.md\"]. Maximum 10 pages."


def build_synthesis_prompt(question: str, index_content: str, schema: str, pages_context: str) -> str:
    return f"""You are querying an LLM Wiki to answer a question. Use the wiki pages below to synthesize a thorough answer. Cite sources using [[PageName]] wikilink syntax.

Schema:
{schema}

Wiki pages:
{pages_context}

Question: {question}

Write a well-structured markdown answer with headers, bullets, and [[wikilink]] citations. At the end, add a ## Sources section listing the pages you drew from.
"""


def query(question: str, save_path: str | None = None, phase1: bool = False, phase2: bool = False):
    today = date.today().isoformat()

    # Step 1: Read index
    index_content = read_file(INDEX_FILE)
    if not index_content:
        print("Wiki is empty. Ingest some sources first with: python tools/ingest.py <source>")
        sys.exit(1)

    # Step 2: Find relevant pages (always runs — keyword matching is fast)
    relevant_pages = find_relevant_pages(question, index_content)

    needs_page_selection = not relevant_pages or len(relevant_pages) <= 1
    schema = read_file(SCHEMA_FILE)
    page_selection_prompt = None

    if needs_page_selection:
        page_selection_prompt = build_page_selection_prompt(question, index_content)

    if phase1:
        tasks = []
        if page_selection_prompt:
            tasks.append({
                "id": "page_selection",
                "prompt": page_selection_prompt,
                "max_tokens": 512,
                "metadata": {"type": "page_selection", "question": question},
            })

        # Build synthesis prompt with whatever pages we have
        pages_context = ""
        for p in relevant_pages:
            rel = p.relative_to(REPO_ROOT)
            pages_context += f"\n\n### {rel}\n{p.read_text(encoding='utf-8')}"
        if not pages_context:
            pages_context = f"\n\n### wiki/index.md\n{index_content}"

        synthesis_prompt = build_synthesis_prompt(question, index_content, schema, pages_context)
        tasks.append({
            "id": "synthesis",
            "prompt": synthesis_prompt,
            "max_tokens": 4096,
            "metadata": {"type": "synthesis", "question": question},
        })

        prepare_tasks(tasks)
        return

    if phase2:
        results_map = read_results()

        # Apply page selection result if needed
        if needs_page_selection and "page_selection" in results_map:
            raw = results_map["page_selection"].strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            try:
                paths = json.loads(raw)
                relevant_pages = [WIKI_DIR / p for p in paths if (WIKI_DIR / p).exists()]
            except (json.JSONDecodeError, TypeError):
                pass

        # Read page content and rebuild synthesis prompt
        pages_context = ""
        for p in relevant_pages:
            rel = p.relative_to(REPO_ROOT)
            pages_context += f"\n\n### {rel}\n{p.read_text(encoding='utf-8')}"
        if not pages_context:
            pages_context = f"\n\n### wiki/index.md\n{index_content}"

        if "synthesis" in results_map:
            answer = results_map["synthesis"]
        else:
            # Fallback: re-synthesize with context
            prompt = build_synthesis_prompt(question, index_content, schema, pages_context)
            answer = call_llm(prompt, max_tokens=4096)

        print("\n" + "=" * 60)
        print(answer)
        print("=" * 60)

        clean_task_dirs()

        # Optionally save
        if save_path is not None:
            if save_path == "":
                slug = input("\nSave as (slug, e.g. 'my-analysis'): ").strip()
                if not slug:
                    print("Skipping save.")
                    return
                save_path = f"syntheses/{slug}.md"

            full_save_path = WIKI_DIR / save_path
            frontmatter = f"""---
title: "{question[:80]}"
type: synthesis
tags: []
sources: []
last_updated: {today}
---

"""
            write_file(full_save_path, frontmatter + answer)

            index_content = read_file(INDEX_FILE)
            entry = f"- [{question[:60]}]({save_path}) — synthesis"
            if "## Syntheses" in index_content:
                index_content = index_content.replace("## Syntheses\n", f"## Syntheses\n{entry}\n")
                INDEX_FILE.write_text(index_content, encoding="utf-8")
            print(f"  indexed: {save_path}")

        append_log(f"## [{today}] query | {question[:80]}\n\nSynthesized answer from {len(relevant_pages)} pages." +
                   (f" Saved to {save_path}." if save_path else ""))
        return

    # ── Default mode: direct LLM calls ──

    # If no keyword match, ask Claude to identify relevant pages from the index
    if needs_page_selection:
        print("  selecting relevant pages via API...")
        prompt = build_page_selection_prompt(question, index_content)
        raw = call_llm(prompt, max_tokens=512)
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            paths = json.loads(raw)
            relevant_pages = [WIKI_DIR / p for p in paths if (WIKI_DIR / p).exists()]
        except (json.JSONDecodeError, TypeError):
            pass

    # Step 3: Read relevant pages
    pages_context = ""
    for p in relevant_pages:
        rel = p.relative_to(REPO_ROOT)
        pages_context += f"\n\n### {rel}\n{p.read_text(encoding='utf-8')}"

    if not pages_context:
        pages_context = f"\n\n### wiki/index.md\n{index_content}"

    # Step 4: Synthesize answer
    print(f"  synthesizing answer from {len(relevant_pages)} pages...")
    prompt = build_synthesis_prompt(question, index_content, schema, pages_context)
    answer = call_llm(prompt, max_tokens=4096)
    print("\n" + "=" * 60)
    print(answer)
    print("=" * 60)

    # Step 5: Optionally save answer
    if save_path is not None:
        if save_path == "":
            # Prompt for filename
            slug = input("\nSave as (slug, e.g. 'my-analysis'): ").strip()
            if not slug:
                print("Skipping save.")
                return
            save_path = f"syntheses/{slug}.md"

        full_save_path = WIKI_DIR / save_path
        frontmatter = f"""---
title: "{question[:80]}"
type: synthesis
tags: []
sources: []
last_updated: {today}
---

"""
        write_file(full_save_path, frontmatter + answer)

        # Update index
        index_content = read_file(INDEX_FILE)
        entry = f"- [{question[:60]}]({save_path}) — synthesis"
        if "## Syntheses" in index_content:
            index_content = index_content.replace("## Syntheses\n", f"## Syntheses\n{entry}\n")
            INDEX_FILE.write_text(index_content, encoding="utf-8")
        print(f"  indexed: {save_path}")

    # Append to log
    append_log(f"## [{today}] query | {question[:80]}\n\nSynthesized answer from {len(relevant_pages)} pages." +
               (f" Saved to {save_path}." if save_path else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the LLM Wiki")
    parser.add_argument("question", help="Question to ask the wiki")
    parser.add_argument("--save", nargs="?", const="", default=None,
                        help="Save answer to wiki (optionally specify path)")
    parser.add_argument("--phase1", action="store_true", help="Write prompts to files for subagent processing")
    parser.add_argument("--phase2", action="store_true", help="Read results from subagent processing")
    args = parser.parse_args()
    query(args.question, args.save, phase1=args.phase1, phase2=args.phase2)
