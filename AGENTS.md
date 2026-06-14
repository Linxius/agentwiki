# LLM Wiki Agent — Schema & Workflow Instructions

## Output Language
`config.json` specifies `"output_language": "zh-CN"`. All wiki output must be written in Simplified Chinese.

This wiki is maintained entirely by your coding agent. No API key needed — just open this repo in Claude Code, OpenCode, or any agent that reads this file, and talk to it. For script-based ingest: `python tools/ingest.py <file>` (requires `litellm` + LLM API).

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

Run `python tools/status.py` — checks pipeline state and suggests next step.
`python tools/status.py --blockers` — show what blocks each step.
`python tools/status.py --next filter` — exit 0/1 if step can run.

## Status Flow

`待处理` → `已深度阅读` → `已合入/已跳过`

---

## Directory Layout

```
raw/          inbox/  inbox.md
              inbox/  YYYY-MM-DD/  *.md
              digest/  brief.md  YYYY-MM-DD/{deepdive-*/,sources/}  brief/
              filter/ papers/ articles/ talks/ books/ projects/ docs/ datasets/
wiki/         index.md log.md overview.md issues.md interests.md
              sources/ entities/ concepts/ syntheses/
graph/        graph.json graph.html
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
5. Clear `inbox.md`

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
7. Clear inbox/   → 用户阅读 `brief.md`，勾选 `[x] 深度阅读` 或 `[x] 合入 wiki` 确定下一步

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
1. **PDF** — `tools/pdf2md.py <path>` (timeout ≥600s). Read `.md` output.
2. **Book splitting** — dir: use chapter files. Single file: split by `##` into `raw/books/<slug>/*.md`.
3. Extract original URL from frontmatter/arXiv ID/content — if none, ask user.
4. Read `wiki/index.md` + `wiki/overview.md` for context.
5. Write source page(s) using template (`templates/`). Set `source_file` + `url`, include `## 原始出处`.
6. **Download images** — `tools/download-images.py <slug>` to `wiki/images/<slug>/`.
7. Update `wiki/index.md` (Sources section) + `wiki/overview.md` (if warranted).
8. Update/create entity (companies/projects/products, **NOT** paper authors) + concept pages.
9. If paper compares with important related work, create source pages for those works.
10. Flag contradictions → `wiki/issues.md` (Contradictions).
11. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <Title>`.
12. **Post-ingest validation** — `validate-wiki.py` checks broken `[[wikilinks]]` + index coverage. Append broken links to `wiki/issues.md` (Phantom Links).
13. Run `health` as post-ingest integrity check.

### Concept Distinction

区分通用概念页（跨论文方法对比，多 sources 标签）与方法具体实现页（单 source 标签），避免混用。例：`FrameGeneration.md`（List 3DWarp/BSR/Mob-FGSR/DLSS3）vs `MobFGSR.md`（论文具体方法）。

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

3. Build structured summary per category (path + description + LLM suggestion).

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

Run: `python tools/build_graph.py --open`

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
