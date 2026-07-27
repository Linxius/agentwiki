#!/usr/bin/env python3
"""Extract compact previews from inbox/ files, dedup by arXiv ID."""
import json, re, sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INBOX_DIR = REPO_ROOT / "raw" / "inbox"

def extract_preview(file_path: Path) -> dict:
    content = file_path.read_text(encoding="utf-8", errors="replace")
    
    # Extract title from YAML frontmatter or first # heading
    title = file_path.stem.replace("-", " ").title()
    yaml_m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if yaml_m:
        fm = yaml_m.group(1)
        t = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
        if t: title = t.group(1)
    else:
        h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1: title = h1.group(1).strip()

    # Extract Abstract (English or Chinese)
    abstract = ""
    for pat in [r'##\s+[Aa]bstract\n(.*?)(?=\n##\s+)', r'##\s+摘要\n(.*?)(?=\n##\s+)', r'\*\*摘要\*\*(.*?)(?=\n##|\Z)']:
        m = re.search(pat, content, re.DOTALL)
        if m:
            abstract = m.group(1).strip()[:2000]
            break
    if not abstract:
        # First 1500 chars after YAML/title
        body = content
        if yaml_m: body = content[yaml_m.end():]
        h1 = re.search(r'^#\s+.+$', body, re.MULTILINE)
        if h1: body = body[h1.end():]
        abstract = body.strip()[:1500]

    return {"file": str(file_path.relative_to(REPO_ROOT)), "title": title, "abstract": abstract[:2000]}

def dedup_by_arxiv(files: list[Path]) -> list[Path]:
    """Keep one .md per arxiv- dir (prefer non-hash-name)."""
    groups = {}
    for f in files:
        parent = f.parent
        if parent.name.startswith("arxiv-"):
            groups.setdefault(parent.name, []).append(f)
        else:
            groups.setdefault(f.name, []).append(f)
    
    result = []
    for key, flist in groups.items():
        if len(flist) == 1:
            result.append(flist[0])
        else:
            # Prefer the one with a descriptive name (not hash-based)
            named = [f for f in flist if not re.search(r'-[a-f0-9]{8}\.md$', f.name)]
            result.append(named[0] if named else flist[0])
    return result

def main():
    files = sorted(INBOX_DIR.rglob("*.md"))
    files = [f for f in files if f.name != "inbox.md"]
    files = dedup_by_arxiv(files)
    
    previews = [extract_preview(f) for f in files]
    
    # Enrich with source_url from content
    for p in previews:
        content = Path(REPO_ROOT / p["file"]).read_text(encoding="utf-8", errors="replace")[:3000]
        for pat in [r'url:\s*["\']?(https?://\S+)["\']?', r'^(https?://\S+)$']:
            m = re.search(pat, content, re.MULTILINE)
            if m:
                p["source_url"] = m.group(1).rstrip('"\'')
                break
        if "source_url" not in p:
            p["source_url"] = ""

    print(json.dumps(previews, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
