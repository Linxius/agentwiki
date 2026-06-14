# LLM Wiki Agent — Schema & Workflow Instructions

## Output Language
`config.json` specifies `"output_language": "zh-CN"`. All wiki output must be written in Simplified Chinese.

Read `config.json` at the repo root for the output language setting. All wiki output should use that language.
This wiki is maintained entirely by your coding agent. No API key or Python scripts needed — just open this repo in Codex, OpenCode, or any agent that reads this file, and talk to it.

Alternatively, you can use the script-based ingest (requires `litellm` + LLM API): `python tools/ingest.py <file>`.

## ⚠️ PDF Handling Rule
**NEVER use the Read tool on `.pdf` files.** Opencode's Read tool does not support PDFs — it will raise an error. Always run `python tools/pdf2md.py <file.pdf>` first, then use `ingest` on the generated `.md` file.

## How to Use

Describe what you want in plain English or use shorthand triggers:

### Pipeline Triggers

| 触发词 | 动作 |
|---|---|
| `feeds` / `拉取 feeds` | 从配置的源拉取新内容到 inbox/ |
| `inbox` / `处理 inbox` | 解析 inbox.md 链接 → 生成 .md 到 inbox/ |
| `filter` / `开始筛选` | 筛选 inbox/ → 生成 digest/brief.md |
| `生成深度阅读` | 对 brief.md 中勾选的条目生成深度阅读 |
| `合入 wiki` / `ingest from digest` | 将 digest 中勾选条目合入 wiki |
| `ingest <file>` | 直接合入单个文件到 wiki |
| `status` / `流程状态` | 检查各流程节点状态并建议下一步 |

### Maintenance Triggers

| 触发词 | 动作 |
|---|---|
| `health` | 结构完整性检查（快速，无 LLM） |
| `lint` | 内容质量检查（慢，需要 LLM） |
| `build graph` | 构建知识图谱 |
| `heal` | 自动补全缺失的实体/概念页 |
| `refresh` | 重新 ingest 已变更的源文档 |

### Query Triggers

| 触发词 | 动作 |
|---|---|
| `query: <question>` | 基于 wiki 内容回答（`python tools/query.py`） |
| *plain question* | 描述需求，如 "ingest this file: raw/papers/...md" |

### Agent Proactive Reminders

The agent should proactively detect and remind about:
- **inbox.md has links**: "inbox.md 中有 N 个链接待处理"
- **New files in inbox/**: "今日有 N 份文件待筛选"
- **Pending deep-read**: brief.md 有 `[x] 深度阅读` 但未生成报告
- **Pending ingest**: brief.md 有 `[x] 合入 wiki` 但未处理
- **After filter completes**: "筛选完成！请阅读 brief.md 确认"

### Status Auto-Detect

Run `python tools/status.py` — script checks pipeline state and suggests next step.

`python tools/status.py --blockers` — show what blocks each step.
`python tools/status.py --next filter` — exit 0/1 if step can run (useful for scripting).

Legacy manual check (if script unavailable):

| 检查点 | 读什么 | 判断 |
|---|---|---|
| inbox.md 链接 | `raw/inbox/inbox.md` | 统计 markdown 链接数 |
| inbox/ 待筛选 | `raw/inbox/` 下日期目录 | 统计 .md 文件数，排除已处理的 |
| brief 最近简报 | `raw/digest/brief.md` | 是否存在、是否有内容 |
| 待深度阅读 | `raw/digest/brief.md` | 扫描 `[x] 深度阅读` 条目 |
| 待合入 wiki | `raw/digest/brief.md` | 扫描 `[x] 合入 wiki` 条目 |
| feeds 配置 | `config.json` → `feeds.sources` | 已配置源的名称和数量 |
| feeds 上次拉取 | `raw/.feeds-state.json` | 读取各源 `last_fetch_date`，为空表示从未拉取 |

输出格式示例：
```
📋 Pipeline Status:
1. inbox: 3 links in inbox.md
2. inbox: 15 files pending filter
3. brief: 2026-06-14 简报已生成
4. deep-read: 2 checked, 0 done
5. ingest: 1 checked, 0 done
6. feeds: 已配置 1 个源，上次拉取 2026-06-14（1天前）

→ 建议: 处理 inbox → filter → 生成深度阅读 → 合入 wiki
```

## Status Flow

`待处理` → `已深度阅读` → `已合入/已跳过`

---

## Directory Layout

```
raw/          inbox/  inbox.md  (link queue)
              inbox/  YYYY-MM-DD/  *.md  (fetched content)
              digest/  brief.md  YYYY-MM-DD/{deepdive-*/,sources/}  brief/
              filter/ papers/ articles/ talks/ books/ projects/ docs/ datasets/
wiki/         index.md log.md overview.md issues.md interests.md
              sources/ entities/ concepts/ syntheses/
graph/        (auto-generated graph data)
templates/    generic.md paper.md article.md book.md dataset.md doc.md project.md talk.md
tools/        inbox.py health.py lint.py build_graph.py filter.py deep-read.py
              download-images.py ingest.py status.py validate-wiki.py
              heal.py refresh.py query.py file_to_md.py pdf2md.py
```

## Link Inbox → Filter → Deep Read → Ingest Workflow

This is the recommended workflow for processing new materials from inbox/ into wiki.

### Pre-step: Inbox Links

Triggered by: *"inbox"* or `python tools/inbox.py`

Steps:
1. Read `raw/inbox/inbox.md` — contains URL links (arXiv IDs, web pages)
2. For each arXiv link → use `arxiv2md` (or fallback to `pdf2md.py`) to convert to markdown
3. For each web URL → use `requests` + `trafilatura` to fetch page and extract readable markdown
4. Save each converted file to `raw/inbox/YYYY-MM-DD/<slug>.md`
5. Clear `inbox.md` (links are removed after processing)

Example `inbox.md` format:
```markdown
# Inbox
- https://arxiv.org/abs/2401.12345
- https://example.com/article
- 2401.12345
```

### Stage 1: Filter

Triggered by: *"filter"* or `python tools/filter.py`

Steps:
1. Scan `raw/inbox/` for files
2. Read `wiki/interests.md`
3. Use LLM to analyze each file:
   - Generate brief summary (3-5 sentences)
   - Generate detailed report (500-800 words in Chinese)
   - Match against interests: `interested` / `possibly_interested` / `not_interested`
   - Suggest category (papers/articles/talks/books/docs/projects/datasets)
4. Generate `raw/digest/brief.md` with entries sorted by match level
   - Each entry includes: title, source URL, matched interests, brief (3-5 sentences), detailed report (500-800 words), checkboxes for [ ] 深度阅读 and [ ] 合入 wiki
   - Entries grouped by match level: `[感兴趣]` → `[可能感兴趣]` → `[不感兴趣]`
5. Move processed files to `raw/digest/YYYY-MM-DD/sources/`
6. Archive current brief.md to `raw/digest/brief/YYYY-MM-DD.md`
7. Clear inbox/

### User: Read brief.md

User reviews `raw/digest/brief.md`, reads brief + detailed report for each entry. Decides which to deep-read and which to ingest into wiki.

- [ ] 深度阅读 — user checks if they want a deep-dive report (~1500-3000 words)
- [ ] 合入 wiki — user checks if they want to ingest into wiki

### Stage 2: Deep Read

Triggered by: *"generate deep-read"* or `python tools/deep-read.py --date YYYY-MM-DD`

Steps:
1. Read brief.md to find entries marked `[x] 深度阅读`
2. For each checked entry, call LLM to generate 1500-3000 word deep-dive report:
   - Core viewpoints deep analysis
   - Technical/methodology breakdown
   - Key data/insights interpretation
   - Comparison with related fields
   - Potential issues/limitations
3. Save report to `raw/digest/YYYY-MM-DD/deepdive-<filename>.md`

### Stage 3: Ingest to Wiki

Triggered by: *"ingest from digest"* or `python tools/ingest.py --from-digest YYYY-MM-DD`

Steps:
1. Read brief.md to find entries marked `[x] 合入 wiki`
2. Find corresponding files in `digest/YYYY-MM-DD/sources/`
3. Show list to user for category confirmation
4. Move files to appropriate category directory (raw/{papers,articles,...}/)
5. Run ingest() for each file (follows existing Ingest Workflow)
6. Update brief.md status

---

## Page Format

Every wiki page uses this frontmatter:

```yaml
---
title: "Page Title"
type: source | entity | concept | synthesis
tags: []
sources: []       # list of source slugs that inform this page
last_updated: YYYY-MM-DD
---
```

Use `[[PageName]]` wikilinks to link to other wiki pages.

---

## Ingest Workflow

Triggered by: *"ingest <file>"*

**Supported formats:** Markdown (`.md`) is ingested directly. Non-markdown files (`.docx`, `.pptx`, `.xlsx`, `.html`, `.txt`, `.csv`, `.json`, `.xml`, `.rst`, `.rtf`, `.epub`, `.ipynb`, `.yaml`, `.yml`, `.tsv`, `.wav`, `.mp3`) are auto-converted to markdown via [markitdown](https://github.com/microsoft/markitdown) before ingestion. PDF files, arXiv IDs, or arXiv URLs are processed via `tools/pdf2md.py`. Use `--no-convert` to skip auto-conversion.

Steps (in order):
1. **PDF preprocessing** — run `tools/pdf2md.py <path-to-pdf>` first (timeout ≥600s). Then read the `.md` output.
2. **Book splitting** — directory (Form B): use existing chapter files. Single file (Form A): split by `##`/`#` headings into `raw/books/<slug>/sourceFile/ch-*.md`, delete original.
3. Extract original URL from frontmatter, arXiv ID, or content — if none found, ask user.
4. Read `wiki/index.md` + `wiki/overview.md` for context.
5. Write source page(s) using the corresponding template (see `templates/`). Set `source_file` to repo-relative raw path, `url` to original URL, include `## 原始出处` section.
6. **Download images** — run `tools/download-images.py <slug>` to fetch external images to `wiki/images/<slug>/` and update paths.
7. Update `wiki/index.md` — add entry under Sources section.
8. Update `wiki/overview.md` — revise synthesis if warranted.
9. Update/create entity pages for companies, projects, products — **DO NOT** create for authors of academic papers.
10. Update/create concept pages for key ideas and frameworks.
11. If paper compares with important related work, create source pages for those works.
12. Flag contradictions — append to `wiki/issues.md` under Contradictions.
13. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <Title>`.
14. **Post-ingest validation** — run `python tools/validate-wiki.py` to check for broken `[[wikilinks]]`, verify all new pages in `index.md`. Append broken links to `wiki/issues.md` under Phantom Links.
15. Run `health` as post-ingest integrity check.

### Important Concept Distinction

When a paper introduces a technique that falls under a broad concept category (e.g., "Frame Generation", "Super Resolution"), distinguish between:

- **Generic concept pages** — cross-paper comparison of different method families (tagged with multiple sources)
- **Method-specific pages** — the concrete technical approach from this specific paper (tagged with the current source)

Example from Mob-FGSR:
- `FrameGeneration.md` — lists 3DWarp, BSR, ExtraNet, Mob-FGSR, DLSS3 as separate techniques
- `MobFGSR.md` — the paper's concrete approach: splatting + quadratic motion modeling

This prevents conflation of different implementations of the same high-level idea.

### Source-Type Templates

All source pages use templates under `templates/`:

- [Generic Template](templates/generic.md) (fallback)
- [Paper](templates/paper.md) / [Article](templates/article.md) / [Book](templates/book.md) / [Dataset](templates/dataset.md) / [Doc](templates/doc.md) / [Project](templates/project.md) / [Talk](templates/talk.md)

Matched by: `raw/{papers,articles,books,datasets,projects,talks}/` prefix in source file path.

---

## Query Workflow

Triggered by: *"query: <question>"*

Steps:
1. Read `wiki/index.md` to identify relevant pages
2. Read those pages
3. Synthesize an answer with inline citations as `[[PageName]]` wikilinks
4. Ask the user if they want the answer filed as `wiki/syntheses/<slug>.md`

---

## Lint Workflow

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

3. Build a structured summary grouped by category with file path, description, and LLM suggestion:
   ```
   ## Orphan Pages
   - `entities/VGGT.md` — 2 outbound links, no inbound. Suggestion: merge (high confidence)

   ## Broken Links
   - `[[DUSt3R]]` — referenced by 3 pages. Suggestion: auto-create stub (high confidence)

   ## Contradictions
   - `sources/paper-a.md` vs `sources/paper-b.md`: DLSS3 frame pacing. Suggestion: favor paper-b (medium confidence)
   ```

4. Present the summary per category: *"Phantom Hubs: 3 eligible. Create stubs? (Y/n)"* etc. User answers per category or skips all.
5. On user confirmation, execute:
   - Auto-create stub entity/concept pages for phantom hubs (no frontmatter beyond title+type, one-line description)
   - Tag orphan pages with `archived: true` in frontmatter or move to `wiki/archived/`
   - Append contradiction annotations to affected pages
   - Update last_updated on stale pages

6. Output a lint report and ask if the user wants it saved to `wiki/lint-report.md`.

7. Sync result to `wiki/issues.md` — remove any issues that were resolved, keep remaining.

---

### interests.md Format

See `wiki/interests.md` for current content. Format:

```yaml
## [Category]
- name: Interest Name
  weight: 0.9
  keywords: [kw1, kw2]
  description: ...
```

## Health Workflow

Triggered by: *"health"* — `python tools/health.py` (zero LLM calls).

Checks (auto-fix, no confirmation needed):
- Empty/stub files (auto-delete)
- Index sync (auto-sync stale/missing entries)
- Log coverage (auto-append missing ingest entries)

Use `--save` for `wiki/health-report.md`.

| vs `lint` | `health` | `lint` |
|---|---|---|
| Scope | Structural | Content quality |
| LLM | Zero | Yes |
| Frequency | Every session | 10-15 ingests |
| Run order | First | After health passes

---

## Graph Workflow

Triggered by: *"build graph"* or *"graph report"*

First try: `python tools/build_graph.py --open`

If Python/deps unavailable, build manually:
1. Search for all `[[wikilinks]]` across wiki pages
2. Build nodes and edges
3. Infer implicit relationships — tag `INFERRED` with confidence score; low confidence → `AMBIGUOUS`
4. Write `graph/graph.json` and `graph/graph.html`

Use `--report` flag for structured graph health:
- **Health summary** — edges/node ratio, orphan %, community count, link density
- **Orphan nodes** — pages with zero graph connections
- **God nodes** — hub pages with degree > μ+2σ
- **Fragile bridges** — community pairs connected by only 1 edge
- **Phantom hubs** — `[[wikilinks]]` referenced by 2+ existing pages but pointing to non-existent pages

Use `--save` to write report to `graph/graph-report.md`.

---

## Naming Conventions

- Source slugs: `kebab-case` matching source filename
- Entity pages: `TitleCase.md` (e.g. `OpenAI.md`, `SamAltman.md`)
- Concept pages: `TitleCase.md` (e.g. `ReinforcementLearning.md`, `RAG.md`)

## Index & Log Format

Index: `## {Section}\n- [Title](path) — one-line`. See `wiki/index.md` for current structure.

Log: `## [YYYY-MM-DD] <operation> | <title>`. Operations: `ingest`, `query`, `health`, `lint`, `graph`, `report`.

> 日期使用操作执行日期（当前实际日期），而非源文档的原始发布日期。

---

## Reply Style
Respond in Chinese with minimal, technical text. No pleasantries, no openings, no summaries. Use newlines and short paragraphs for clarity. This rule applies to text responses only; code, comments, and commit messages remain as usual.
