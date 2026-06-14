# Graph Workflow

Triggered by: *"build graph"* or *"graph report"*

Run: `python tools/build_graph.py --open`

Use `--report` flag for structured graph health:
- **Health summary** — edges/node ratio, orphan %, community count, link density
- **Orphan nodes** — pages with zero graph connections
- **God nodes** — hub pages with degree > μ+2σ
- **Fragile bridges** — community pairs connected by only 1 edge
- **Phantom hubs** — `[[wikilinks]]` referenced by 2+ existing pages but pointing to non-existent pages

Use `--save` to write report to `graph/graph-report.md`.
