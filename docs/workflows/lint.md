# Lint Workflow

Triggered by: *"lint"*

### Steps

1. Build or load graph (`python tools/build_graph.py --report`):
   - Builds graph from all `[[wikilinks]]` across wiki pages
   - Runs graph-aware structural checks: **orphan pages**, **broken links**, **sparse pages**, **pending entities**, **phantom hubs**, **hub stubs**, **fragile bridges**, **isolated communities**

2. For each problem category, use LLM for semantic analysis:
   - **Orphan pages** — assess whether the page has standalone value (merge candidate vs. delete candidate vs. keep but add links)
   - **Contradictions** — cross-page claims that conflict; LLM judges which is likely correct or if both can coexist
   - **Stale summaries** — pages whose last_updated predates newer source pages on the same topic; LLM determines if content is still current
   - **Misclassification** — pages whose `type: entity|concept` seems wrong given their content; LLM suggests the correct type
   - **Data gaps** — questions the wiki can't answer; LLM suggests new source types to seek

3. Build structured summary per category (path + description + LLM suggestion).

4. Present the summary per category: *"Phantom Hubs: 3 eligible. Create stubs? (Y/n)"* etc. User answers per category or skips all.
5. On user confirmation, execute:
   - Auto-create stub entity/concept pages for phantom hubs (no frontmatter beyond title+type, one-line description)
   - Tag orphan pages with `archived: true` in frontmatter or move to `wiki/archived/`
   - Append contradiction annotations to affected pages
   - Update last_updated on stale pages

6. Output a lint report and ask if the user wants it saved to `wiki/lint-report.md`.

7. Sync result to `wiki/issues.md` — remove any issues that were resolved, keep remaining.

### interests.md Format

See `wiki/interests.md` for current content. Format:

```yaml
## [Category]
- name: Interest Name
  weight: 0.9
  keywords: [kw1, kw2]
  description: ...
```
