"""Feeds — pull new content from configured sources into inbox."""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / "config.json"
STATE_FILE = REPO_ROOT / "raw" / ".feeds-state.json"
INBOX_DIR = REPO_ROOT / "raw" / "inbox"

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_PAGE_SIZE = 100

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def yesterday_str():
    """Return most recent weekday (Mon-Fri). arXiv doesn't publish on weekends."""
    d = datetime.now(timezone.utc) - timedelta(days=1)
    if d.weekday() >= 5:
        d -= timedelta(days=d.weekday() - 4)
    return d.strftime("%Y-%m-%d")


def arxiv_date_param(d):
    """Convert YYYY-MM-DD to arXiv API date format YYYYMMDDHHMMSS."""
    return d.replace("-", "") + "0000"


def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)


def load_processed(source_name):
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            all_state = json.load(f)
    else:
        all_state = {}
    return all_state.get(source_name, {"processed_ids": [], "last_fetch_date": None})


def save_processed(source_name, data):
    all_state = {}
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            all_state = json.load(f)
    all_state[source_name] = data
    ensure_dir(STATE_FILE.parent)
    with open(STATE_FILE, "w") as f:
        json.dump(all_state, f, indent=2, ensure_ascii=False)


def fetch_arxiv_page(url, start):
    full_url = f"{url}&max_results={ARXIV_PAGE_SIZE}&start={start}"
    print(f"  Fetching start={start}...")
    resp = requests.get(full_url, timeout=30)
    resp.raise_for_status()
    return ET.fromstring(resp.content)


def parse_arxiv_entry(entry):
    raw_id = entry.find("atom:id", NS).text.strip()
    arxiv_id = raw_id.split("/")[-1].split("v")[0] if "/" in raw_id else raw_id

    title = entry.find("atom:title", NS).text.strip().replace("\n", " ").replace("  ", " ")
    summary = entry.find("atom:summary", NS).text.strip().replace("\n", " ").replace("  ", " ")
    published = entry.find("atom:published", NS).text.strip()

    authors = []
    for author in entry.findall("atom:author", NS):
        name = author.find("atom:name", NS)
        if name is not None:
            authors.append(name.text.strip())

    cats = []
    for cat in entry.findall("atom:category", NS):
        term = cat.attrib.get("term", "")
        if term.startswith("cs."):
            cats.append(term)

    link = ""
    for l in entry.findall("atom:link", NS):
        if l.attrib.get("rel", "") == "alternate":
            link = l.attrib.get("href", "")
            link = re.sub(r"v\d+$", "", link)
            break

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "abstract": summary,
        "authors": authors,
        "categories": cats,
        "published": published,
        "link": link,
    }


def fetch_arxiv_feed(categories, since_date, until_date, processed_ids):
    """Query arXiv API for papers in date range, paginating for all results."""
    cat_query = "+OR+".join(f"cat:{c}" for c in categories)
    sd = arxiv_date_param(since_date)
    ed = arxiv_date_param(until_date)
    base_url = (f"{ARXIV_API}?search_query=({cat_query})+AND+submittedDate:[{sd}+TO+{ed}]"
                f"&sortBy=submittedDate&sortOrder=descending")

    new_entries = []
    start = 0
    empty_pages = 0

    while True:
        try:
            feed = fetch_arxiv_page(base_url, start)
        except Exception as e:
            print(f"  Error: {e}")
            break

        entries = feed.findall("atom:entry", NS)
        if not entries:
            empty_pages += 1
            if empty_pages >= 2:
                break
            start += ARXIV_PAGE_SIZE
            continue
        empty_pages = 0

        for entry in entries:
            parsed = parse_arxiv_entry(entry)
            if parsed["arxiv_id"] not in processed_ids:
                new_entries.append(parsed)

        start += ARXIV_PAGE_SIZE
        time.sleep(0.3)

    return new_entries


def write_inbox_entry(source_name, entry):
    date = entry["published"][:10]
    out_dir = INBOX_DIR / date
    ensure_dir(out_dir)

    filename = f"{source_name}-{entry['arxiv_id']}.md"
    out_path = out_dir / filename

    if out_path.exists():
        return None

    authors_str = ", ".join(entry["authors"])
    cats_str = ", ".join(entry["categories"])

    content = f"""---
title: "{entry['title']}"
arxiv_id: "{entry['arxiv_id']}"
url: "{entry['link']}"
categories: [{','.join(entry['categories'])}]
source_feed: "{source_name}"
---

**标题**: {entry['title']}
**作者**: {authors_str}
**分类**: {cats_str}
**arXiv**: {entry['link']}
**提交日期**: {entry['published'][:10]}

**摘要**:
{entry['abstract']}
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

    return out_path


def process_arxiv_source(source):
    name = source["name"]
    categories = source["categories"]
    print(f"\n[{name}] Processing...")

    processed = load_processed(name)
    processed_ids = set(processed.get("processed_ids", []))

    yesterday = yesterday_str()

    if processed["last_fetch_date"] is None:
        since_date = yesterday
        print(f"  First run — fetching only {since_date}")
    else:
        since_date = processed["last_fetch_date"]
        if since_date >= yesterday:
            print(f"  Already up to date (last: {since_date})")
            return 0

    print(f"  Date range: {since_date} → {yesterday}")

    entries = fetch_arxiv_feed(categories, since_date, yesterday, processed_ids)

    if not entries:
        print(f"  No new entries.")
        new_ids = set()
    else:
        print(f"  Found {len(entries)} new entries.")
        new_ids = set()
        count = 0
        for entry in entries:
            path = write_inbox_entry(name, entry)
            if path:
                count += 1
            new_ids.add(entry["arxiv_id"])
        print(f"  Wrote {count} files to inbox/.")

    combined_ids = processed_ids | new_ids
    save_processed(name, {
        "processed_ids": sorted(combined_ids),
        "last_fetch_date": yesterday,
    })

    return len(entries)


def main():
    if not CONFIG_FILE.exists():
        print(f"Config not found: {CONFIG_FILE}")
        print("Create config.json at repo root with feeds.sources.")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    sources = config.get("feeds", {}).get("sources", [])
    if not sources:
        print("No sources defined in config.json")
        sys.exit(1)

    total = 0
    for source in sources:
        if not source.get("enabled", True):
            print(f"\n[{source['name']}] Skipped (disabled)")
            continue
        if source["type"] == "arxiv":
            total += process_arxiv_source(source)
        else:
            print(f"\n[{source['name']}] Unknown type: {source['type']}")

    print(f"\nDone. {total} total new entries added to inbox/.")


if __name__ == "__main__":
    main()
