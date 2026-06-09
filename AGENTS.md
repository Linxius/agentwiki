# LLM Wiki Agent — Schema & Workflow Instructions

## Output Language
`config.json` specifies `"output_language": "zh-CN"`. All wiki output must be written in Simplified Chinese.

Read `config.json` at the repo root for the output language setting. All wiki output should use that language.
This wiki is maintained entirely by your coding agent. No API key or Python scripts needed — just open this repo in Codex, OpenCode, or any agent that reads this file, and talk to it.

Alternatively, you can use the script-based ingest (requires `litellm` + LLM API): `python tools/ingest.py <file>`.

## ⚠️ PDF Handling Rule
**NEVER use the Read tool on `.pdf` files.** Opencode's Read tool does not support PDFs — it will raise an error. Always run `python tools/pdf2md.py <file.pdf>` first, then use `ingest` on the generated `.md` file.

## How to Use

Describe what you want in plain English:
- *"Ingest this file: raw/papers/my-paper.md"*
- *"What does the wiki say about transformer models?"*
- *"Check the wiki for orphan pages and contradictions"*
- *"Build the knowledge graph"*

Or use shorthand triggers:
- `filter` → runs the Filter Workflow (scan raw/inbox/ based on interests)
- `ingest <file>` → runs the Ingest Workflow (auto-converts PDF via pdf2md.py)
- `ingest from daily YYYY-MM-DD` → runs Ingest from daily brief
- `query: <question>` → runs the Query Workflow
- `health` → runs the Health Workflow (fast, every session)
- `lint` → runs the Lint Workflow (expensive, periodic)
- `build graph` → runs the Graph Workflow

### Agent Proactive Reminders

The agent should proactively detect and remind about:
- **New files in inbox/**: Alert user "今日有 N 份文件待筛选" when files are added
- **Pending deep-read**: When brief.md has `[x] 深度阅读` but no deepdive report yet
- **Pending ingest**: When brief.md has `[x] 合入 wiki` but not yet processed
- **After filter completes**: "筛选完成！报告已生成，请阅读 brief.md 确认"

User can also trigger actions directly:
- "开始筛选" → agent runs filter
- "生成深度阅读" → agent generates deepdive for checked entries
- "合入 wiki" → agent processes ingested entries from daily/

## Brief.md Format

```markdown
# 资讯简报  2025-06-10

## [感兴趣]

### article1.pdf
- 来源: https://arxiv.org/abs/xxx.xxxxx
- 匹配: transformers, attention
- 理由: 核心主题与用户兴趣高度相关
- [x] 深度阅读
- [ ] 合入 wiki

**简介**：LLM 3-5 句简介...

**详细报告**：
500-800 字详细报告...
```

## Status Flow

`待处理` → `已深度阅读` → `已合入/已跳过`

---

## Directory Layout

```
raw/          # Source documents
  inbox/      # Pending filter — new materials arrive here
  daily/      # Daily briefings and deep-read reports
    brief.md  # Today's brief report with entries sorted by interest match
    YYYY-MM-DD/
      deepdive-*.md  # Deep-dive reading reports (generated after user confirmation)
      sources/       # Original files moved during filter
    brief/      # Archived brief reports (YYYY-MM-DD.md)
  filter/     # Legacy filter reports
  papers/     # Academic papers
  articles/   # Blogs, tutorials, reports
  talks/      # Conference talks, slides
  books/      # Books
  projects/   # Projects, codebases
  docs/       # Documentation, whitepapers
  datasets/   # Datasets, benchmarks
wiki/         # Agent owns this layer entirely
  index.md    # Catalog of all pages — update on every ingest
  log.md      # Append-only chronological record
  overview.md # Living synthesis across all sources
  issues.md   # Known issues: pending entities, phantom links, contradictions, etc.
  interests.md # User interests for filter matching
  sources/    # One summary page per source document
  entities/   # People, companies, projects, products
  concepts/   # Ideas, frameworks, methods, theories
  syntheses/  # Saved query answers
graph/        # Auto-generated graph data
tools/        # Standalone Python scripts
  health.py   # Structural checks (deterministic, no LLM calls)
  lint.py     # Content quality checks (uses LLM for semantic analysis)
  build_graph.py  # Knowledge graph generation
  filter.py   # Filter and classify raw/inbox/ files → generates raw/daily/brief.md
  deep-read.py  # Generate deep-dive reports from checked brief entries
  ingest.py   # Ingest source documents into wiki (supports --from-daily)
```

## Filter → Deep Read → Ingest Workflow (New)

This is the recommended workflow for processing new materials from inbox/ into wiki.

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
4. Generate `raw/daily/brief.md` with entries sorted by match level
   - Each entry includes: title, source URL, matched interests, brief (3-5 sentences), detailed report (500-800 words), checkboxes for [ ] 深度阅读 and [ ] 合入 wiki
   - Entries grouped by match level: `[感兴趣]` → `[可能感兴趣]` → `[不感兴趣]`
5. Move processed files to `raw/daily/YYYY-MM-DD/sources/`
6. Archive current brief.md to `raw/daily/brief/YYYY-MM-DD.md`
7. Clear inbox/

### User: Read brief.md

User reviews `raw/daily/brief.md`, reads brief + detailed report for each entry. Decides which to deep-read and which to ingest into wiki.

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
3. Save report to `raw/daily/YYYY-MM-DD/deepdive-<filename>.md`

### Stage 3: Ingest to Wiki

Triggered by: *"ingest from daily"* or `python tools/ingest.py --from-daily YYYY-MM-DD`

Steps:
1. Read brief.md to find entries marked `[x] 合入 wiki`
2. Find corresponding files in `daily/YYYY-MM-DD/sources/`
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
1. **PDF preprocessing** (only for `.pdf` files) — **NEVER use the Read tool to directly read `.pdf` files**. Always run `tools/pdf2md.py <path-to-pdf>` first (timeout at least 600000ms). The script handles conversion, title extraction, PDF rename, and images. Then read the generated `.md` file and continue with the rest of the workflow.
2. **Book splitting** (if source is under `raw/books/`):
   - **If source is a directory** (Form B): skip splitting, use existing chapter files under `sourceFile/`.
   - **If source is a single file** (Form A): split into chapters by scanning `##` or `#` heading boundaries. Generate `raw/books/<slug>/sourceFile/ch-<NN>-<topic>.md` files. Delete the original single file after splitting. Then continue with directory mode.
3. Read the source document fully
4. Read `wiki/index.md` and `wiki/overview.md` for current wiki context
5. Write source page(s):
   - **For books (Form B)**: write `wiki/sources/<book-slug>/overview.md` (overview page) + `wiki/sources/<book-slug>/ch-<NN>-<topic>.md` (one per chapter). Use the Book Directory Template.
   - **For all other sources**: write `wiki/sources/<slug>.md` using the appropriate source-type template.
6. **Download images** — scan source pages for external image URLs (`http://`, `https://`, `data:image/`), download to `wiki/images/<slug>/`, and update paths to `../images/<slug>/filename`. For books, use `wiki/images/<book-slug>/ch<N>/`.
7. Update `wiki/index.md` — add entry under Sources section. For books (Form B), add only one link to the overview page (e.g., `- [Book Title](sources/<book-slug>/overview.md)`).
8. Update `wiki/overview.md` — revise synthesis if warranted
9. Update/create entity pages for key companies, projects, products mentioned — **DO NOT create entity pages for authors or individual people when ingesting academic papers**
10. Update/create concept pages for key ideas and frameworks discussed
11. If the paper compares with important related work, create source pages for those compared works
12. Flag any contradictions with existing wiki content — append to `wiki/issues.md` under Contradictions section
13. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <Title>`
14. **Post-ingest validation** — check for broken `[[wikilinks]]`, verify all new pages are in `index.md`, print a change summary. Append any broken wikilinks to `wiki/issues.md` under Phantom Links section.
15. Run `health` as post-ingest integrity check.

### Important Concept Distinction

When a paper introduces a technique that falls under a broad concept category (e.g., "Frame Generation", "Super Resolution"), distinguish between:

- **Generic concept pages** — cross-paper comparison of different method families (tagged with multiple sources)
- **Method-specific pages** — the concrete technical approach from this specific paper (tagged with the current source)

Example from Mob-FGSR:
- `FrameGeneration.md` — lists 3DWarp, BSR, ExtraNet, Mob-FGSR, DLSS3 as separate techniques
- `MobFGSR.md` — the paper's concrete approach: splatting + quadratic motion modeling

This prevents conflation of different implementations of the same high-level idea.

### Source Page Format

所有 source 页面使用的通用模板（可根据具体内容调整，不需要完全遵从）：

```markdown
---
title: "Source Title"
type: source
tags: []
date: YYYY-MM-DD
source_file: raw/...
links: []         # 代码或项目链接
---

## Summary
2–4 sentence summary.

## Key Points
- Point 1
- Point 2

## Relevance
与 [[EntityName]] 或 [[ConceptName]] 的关联。

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

### Source-Type Templates

If the source file path starts with `raw/articles/`, `raw/books/`, `raw/datasets/`, `raw/docs/`, `raw/papers/`, `raw/projects/`, or `raw/talks/`, use the corresponding template below instead of the default generic one above.

#### Paper Template (`raw/papers/`)
```markdown
---
title: "Paper Title"
type: source
tags: [paper]
date: YYYY-MM-DD
source_file: raw/papers/...
venue: ""          # 会议或期刊名，如 CVPR 2025
published: YYYY    # 发表年份
links: []          # 代码或项目链接
---

## Summary
2–4 句概述论文解决的问题、核心方法和主要贡献。

## Key Contributions
- Contribution 1
- Contribution 2

## Method
详细描述论文的核心方法、技术流程、算法步骤和实现细节。包括模型架构、训练策略、关键模块设计、数据流和推理过程。避免泛泛而谈，要写出可复现的技术细节。

核心架构概览，包括 pipeline 结构、输入输出、关键模块及其交互关系。可使用流程图辅助说明。

**模块/组件细节**：
- **组件 1**: 功能、设计选择和数学公式（如有）
- **组件 2**: 同上

**论文中的框架图、流程图、步骤图等必须写入**：引用时使用 `![描述](../images/<source-slug>/文件名)` 格式（注意路径相对于 `wiki/sources/`），图片放在对应标题下方并附简要文字说明。不要遗漏任何与技术流程相关的图示。

**下载外部图片**：所有图片必须保存在本地 `wiki/images/<source-slug>/` 目录下。使用 `curl` 或 `wget` 下载图片到该目录，图片文件名保持简洁（如 `pipeline.png`、`architecture.png`、`results.png`）。如果源文档中图片是 base64 嵌入，需提取并保存为独立图片文件。

## Training
- 目标函数 / Loss 设计
- 训练策略、超参数、调度器
- 数据需求与预处理

## Results & Comparisons
总结论文的实验结果，特别是与相关工作中其他方法的对比数据。包括指标对比、优劣分析。如果对比了重要工作，记录对比结果，并分析论文方法与对应相关工作的**相同点和不同点**（设计思路、假设条件、适用场景等）。

## Related Work Analysis
如果论文本身没有在 Results 中详细对比某个重要相关工作，在此处补充：列出论文与该工作的关键异同，包括技术路线、假设条件和性能差异。

## Ablations
关键消融实验及其结论，提炼每个消融揭示的设计原则。

## Limitations
论文自述的局限性，或 reviewer 指出的问题。

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

#### Article Template (`raw/articles/`)
```markdown
---
title: "Article Title"
type: source
tags: [article]
date: YYYY-MM-DD
source_file: raw/articles/...
---

## Summary
2–4 sentence summary.

## Key Points
- Point 1
- Point 2

## Analysis
深度分析文章的核心论点、论据和结论。包括作者立场、数据支撑、逻辑链条。

## Relevance
与 [[EntityName]] 或 [[ConceptName]] 的关联。

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

#### Book Template (`raw/books/`)

Books can be ingested in two forms:

**Form A — Single markdown file** (e.g., PDF converted to one large MD): follows the single-page template below.

**Form B — Directory with pre-split chapter files** (e.g., `raw/books/<book>/sourceFile/ch-*.md`): generates an overview page + one source page per chapter.

In both forms, the ingest workflow handles splitting (see [Ingest Workflow](#ingest-workflow)).

##### Single File Template (Form A)
```markdown
---
title: "Book Title"
type: source
tags: [book]
date: YYYY-MM-DD
source_file: raw/books/...
---

## Summary
2–4 sentence summary of the book.

## Structure
- Chapter N: [Title] — key idea
- Chapter N: [Title] — key idea

## Key Concepts
- [[ConceptName]] — how it connects

## Connections
- [[EntityName]] — how they relate

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

##### Book Directory Template (Form B)

###### Overview Page (`wiki/sources/<book-slug>/overview.md`)
```markdown
---
title: "Book Title"
type: source
tags: [book]
date: YYYY-MM-DD
source_file: raw/books/<book>/
---

## Summary
2–4 sentence summary of the book.

## Chapters
- [[Ch01Introduction|Ch1: Introduction]]
- [[Ch02GraphicsPipeline|Ch2: Graphics Pipeline]]
- ...

## Key Concepts
- [[ConceptName]] — how it connects

## Connections
- [[EntityName]] — how they relate

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

###### Chapter Page (`wiki/sources/<book-slug>/ch-<NN>-<topic>.md`)
```markdown
---
title: "Ch<N>: Chapter Title"
type: source
tags: [book-chapter]
date: YYYY-MM-DD
source_file: raw/books/<book>/sourceFile/...
book: "Book Title"
---

## Summary
2–4 sentence summary of the chapter.

## Key Points
- Point 1
- Point 2

## Key Concepts
- [[ConceptName]] — how it connects

## Connections
- [[ChapterX]] — how it relates to other chapters
- [[EntityName]] — how they relate
```

#### Dataset Template (`raw/datasets/`)
```markdown
---
title: "Dataset Name"
type: source
tags: [dataset]
date: YYYY-MM-DD
source_file: raw/datasets/...
code_url: ""
---

## Summary
2–4 sentence description.

## Statistics
- Size: ...
- Splits: ...
- Annotation types: ...

## Collection Methodology
如何收集、标注、清洗数据的。

## Key Characteristics
- Unique aspects vs similar datasets

## Usage
常见使用场景和基准任务。

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects
```

#### Doc Template (`raw/docs/`)
```markdown
---
title: "Document Title"
type: source
tags: [doc]
date: YYYY-MM-DD
source_file: raw/docs/...
---

## Summary
2–4 sentence summary.

## Architecture / Design
核心架构概述、技术选型、模块划分和数据流。

## Installation
环境和依赖安装步骤。

## Usage
基本用法和典型示例。

## Key Sections
- Section — key content

## Key Takeaways
- Takeaway 1
- Takeaway 2

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects
```

#### Project Template (`raw/projects/`)
```markdown
---
title: "Project Name"
type: source
tags: [project]
date: YYYY-MM-DD
source_file: raw/projects/...
code_url: ""
---

## Summary
2–4 sentence description.

## Goals & Motivation

## Architecture / Design
核心架构、技术选型、模块划分。

## Installation
环境和依赖安装步骤。

## Usage
安装后的基本用法和典型示例。

## Key Results
- Result 1
- Result 2

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects
```

#### Talk Template (`raw/talks/`)
```markdown
---
title: "Talk Title"
type: source
tags: [talk]
date: YYYY-MM-DD
source_file: raw/talks/...
---

## Summary
2–4 sentence summary.

## Key Points
- Point 1
- Point 2

## Speaker's Argument
演讲者的核心论点、论据和结论。

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

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

3. Build a structured summary grouped by category, listing each item with:
   - File path
   - Brief description of the issue
   - LLM's suggestion (action + confidence)
   - Example:
     ```
     ## Orphan Pages
     - `entities/VGGT.md` — 2 outbound links, no inbound. Suggestion: merge into sources/mob-fgsr.md (high confidence)
     - `concepts/FrameGeneration.md` — 0 links total. Suggestion: delete (high confidence)

     ## Broken Links (Phantom Hubs)
     - `[[DUSt3R]]` — referenced by 3 pages. Suggestion: auto-create stub entity page (high confidence)
     - `[[MegaSaM]]` — referenced by 1 page. Recorded to issues.md, no action needed.

     ## Contradictions
     - `sources/paper-a.md` vs `sources/paper-b.md`: claims about DLSS3 frame pacing. Suggestion: resolve in favor of paper-b (medium confidence)

     ## Pending Entities
     - `[[VGGT]]` — referenced by 5 pages. Suggestion: create entity page (high confidence)
     - `[[DUSt3R]]` — referenced by 3 pages. Suggestion: create entity page (medium confidence)

     ## Misclassification
     - `concepts/DUSt3R.md` — describes a specific model, not a general concept. Suggestion: reclassify as entity (high confidence)
     - `entities/FrameGeneration.md` — describes a broad technique category. Suggestion: reclassify as concept (high confidence)
     ```

4. Present the summary to the user with a prompt for each actionable category:
   ```
   Phantom Hubs: 3 eligible for auto-create. Create stub pages? (Y/n)
   Orphan pages: 2 candidates. Archive/delete them? (Y/n)
   Contradictions: 1 found. Apply suggested resolution? (Y/n)
   Pending Entities: 2 eligible for creation. Create pages? (Y/n)
   Misclassification: 2 found. Apply reclassifications? (Y/n)
   ```
   The user can answer per category or skip all.

5. On user confirmation, execute the actions:
   - Auto-create stub entity/concept pages for phantom hubs (no frontmatter beyond title+type, one-line description)
   - Tag orphan pages with `archived: true` in frontmatter or move to `wiki/archived/`
   - Append contradiction annotations to affected pages
   - Update last_updated on stale pages

6. Output a lint report and ask if the user wants it saved to `wiki/lint-report.md`.

7. Sync result to `wiki/issues.md` — remove any issues that were resolved, keep remaining.

---

## Filter Workflow

Triggered by: *"filter"*

Scan `raw/inbox/`, match against `wiki/interests.md`, and classify files.

Steps:
1. Scan `raw/inbox/` for supported files
2. Read `wiki/interests.md` for current interests
3. Use LLM to do full-text semantic matching against interests
4. Rank results by match level: 感兴趣/可能感兴趣/不感兴趣
5. Output Markdown report to `raw/filter/filter-YYYY-MM-DD.md`
   - Same day: append new batch, mark old entries as [已筛选]
   - Each entry: title, description, matched interests, suggested category, checkbox
6. Interactive confirmation: user selects files to keep
7. Move files to corresponding category (papers/articles/talks/books/docs/projects/datasets)
8. Prompt to clear `inbox/` after successful classification
9. Append to `wiki/log.md`: `## [YYYY-MM-DD] filter | N files classified`

### interests.md Format

```yaml
---
title: "兴趣点"
type: synthesis
tags: [interests]
sources: []
last_updated: YYYY-MM-DD
---

## [Category Name]
- name: Interest Name
  weight: 0.9
  keywords: [keyword1, keyword2]
  description: Fuzzy description for matching
```

## Health Workflow

Triggered by: *"health"*

Run: `python tools/health.py` (or `python tools/health.py --json` for machine-readable output)

Fast structural integrity checks — **zero LLM calls**, safe to run every session:
- **Empty / stub files** — pages with no content beyond frontmatter (rate-limit damage). Auto-delete.
- **Index sync** — `wiki/index.md` entries vs actual files on disk. Auto-sync (remove stale entries, warn on missing pages).
- **Log coverage** — source pages missing a corresponding `ingest` entry in `wiki/log.md`. Auto-append.

No user confirmation needed for any fix. Output a health report after repair. Use `--save` to write to `wiki/health-report.md`.

---

### Health vs Lint Boundary

| Dimension | `health` | `lint` |
|---|---|---|
| **Scope** | Structural integrity | Content quality |
| **LLM calls** | Zero | Yes (semantic analysis) |
| **Cost** | Free | Tokens |
| **Frequency** | Every session, before other work | Every 10-15 ingests |
| **Checks** | Empty files, index sync, log sync | Orphans, broken links, contradictions, gaps |
| **Tool** | `tools/health.py` | `tools/lint.py` |
| **Run order** | First (pre-flight) | After health passes |

> Run `health` first — linting an empty file wastes tokens.

---

## Graph Workflow

Triggered by: *"build graph"*

First try: `python tools/build_graph.py --open`

If Python/deps unavailable, build manually:
1. Search for all `[[wikilinks]]` across wiki pages
2. Build nodes (one per page) and edges (one per link)
3. Infer implicit relationships not captured by wikilinks — tag `INFERRED` with confidence score; low confidence → `AMBIGUOUS`
4. Write `graph/graph.json` with `{nodes, edges, built: date}`
5. Write `graph/graph.html` as a self-contained vis.js visualization

---

## Naming Conventions

- Source slugs: `kebab-case` matching source filename
- Entity pages: `TitleCase.md` (e.g. `OpenAI.md`, `SamAltman.md`)
- Concept pages: `TitleCase.md` (e.g. `ReinforcementLearning.md`, `RAG.md`)

## Index Format

```markdown
# Wiki Index

## Overview
- [Overview](overview.md) — living synthesis

## Sources
- [Source Title](sources/slug.md) — one-line summary

## Entities
- [Entity Name](entities/EntityName.md) — one-line description

## Concepts
- [Concept Name](concepts/ConceptName.md) — one-line description

## Syntheses
- [Analysis Title](syntheses/slug.md) — what question it answers
```

## Log Format

`## [YYYY-MM-DD] <operation> | <title>`

Operations: `ingest`, `query`, `health`, `lint`, `graph`, `report`

> 日期使用操作执行日期（当前实际日期），而非源文档的原始发布日期。

---

## Graph Health Report

Triggered by: *"graph report"* or `python tools/build_graph.py --report`

The `--report` flag generates a structured graph health report covering:
- **Health summary** — edges/node ratio, orphan %, community count, link density
- **Orphan nodes** — pages with zero graph connections
- **God nodes** — hub pages with degree > μ+2σ (disproportionate connectivity)
- **Fragile bridges** — community pairs connected by only 1 edge
- **Phantom hubs** — `[[wikilinks]]` referenced by 2+ existing pages but pointing to non-existent pages (page creation signals)

Use `--save` to write the report to `graph/graph-report.md`.

---

## Phase 3 Design Constraints (Auto-Linking — Open)

Phase 3 proposes automatic `[[wikilink]]` insertion based on graph analysis. The following hard rules apply:

### Promotion Gate: `draft → stable`
- Auto-linked edges start as `DRAFT` (visible in graph, not written to page body)
- A dedicated `promote` pass validates source grounding + consistency
- Only edges that pass get materialized as `[[wikilinks]]` in the page
- **Link density budget**: a page must have ≥2 outbound wikilinks before promotion

### Hard Rules
| ID | Rule | Rationale |
|---|---|---|
| HG-WA-01 | Graph layer MUST NOT auto-create pages from broken links — report only | LLM ingest produces hallucinated wikilinks; auto-creating amplifies noise |
| HG-WA-02 | New slash commands MUST NOT duplicate existing command coverage | Prevents user confusion; merge into existing commands instead |

## Reply Style
Respond in Chinese with minimal, technical text. No pleasantries, no openings, no summaries. Use newlines and short paragraphs for clarity. This rule applies to text responses only; code, comments, and commit messages remain as usual.
