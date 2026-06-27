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
| `deep read` / `生成深度阅读` | 对 brief.md 中勾选的条目生成深度阅读 |
| `合入 wiki` / `ingest from digest` | 将 digest 中勾选条目合入 wiki |
| `ingest <file>` | 直接合入单个文件到 wiki |
| `read code` / `代码阅读` | 子代理驱动：收集代码 → 分析 → 生成 wiki 页面（见 Code Reading Workflow） |
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

The agent should proactively detect and remind with trigger words:
- **inbox.md has links**: "inbox.md 中有 N 个链接待处理（触发词: inbox）"
- **inbox/ has files**: "今日有 N 份文件待筛选（触发词: filter）"
- **Pending deep-read**: "brief.md 有 `[x] 深度阅读` 但未生成报告（触发词: deep read）"
- **Pending ingest**: "brief.md 有 `[x] 合入 wiki` 但未处理（触发词: ingest from digest）"
- **Feeds stale**: "feeds 已 N 天未拉取（触发词: feeds）"
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
               digest/  brief.md  YYYY-MM-DD/{deepdive-*/,}  sources/YYYY-MM-DD/  brief/
              filter/ papers/ articles/ talks/ books/ projects/ docs/ datasets/ codes/
wiki/         index.md log.md overview.md issues.md interests.md
              sources/ entities/ concepts/ syntheses/
graph/        graph.json graph.html
templates/    generic.md paper.md article.md book.md dataset.md doc.md project.md talk.md
tools/        inbox.py health.py lint.py build_graph.py filter.py deep-read.py
              download-images.py ingest.py status.py validate-wiki.py
              heal.py refresh.py query.py file_to_md.py pdf2md.py code-read.py
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
2. Read `wiki/interests.md`（含 `## 兴趣列表` 和 `## 排除列表` 两个分区）
3. Use LLM to analyze each file:
   - Generate brief summary (3-5 sentences)
   - Generate detailed report (500-800 words in Chinese)
   - Match against interests: `interested` / `possibly_interested` / `not_interested`
   - Match against exclusion list: 命中则强制 `not_interested`
   - Suggest category (papers/articles/talks/books/docs/projects/datasets)
   - Optionally suggest new interests/disinterests via `suggested_new_interests` / `suggested_new_disinterests`
4. Generate `raw/digest/brief.md` with entries sorted by match level
   - Each entry includes: title, source URL, matched interests, brief (3-5 sentences), detailed report (500-800 words), checkboxes for [ ] 深度阅读、[ ] 合入 wiki、[ ] 不感兴趣
   - Entries grouped by match level: `[感兴趣]` → `[可能感兴趣]`（`[不感兴趣]` 不写入 brief）
5. Move processed files to `raw/digest/YYYY-MM-DD/sources/`
6. Archive current brief.md to `raw/digest/brief/YYYY-MM-DD.md`
7. Clear inbox/   → 用户阅读 `brief.md`，勾选 `[x] 深度阅读`、`[x] 合入 wiki` 或 `[x] 不感兴趣` 确定下一步
   - 控制台会汇总 LLM 建议的新增兴趣/排除项供参考

### Stage 2: Deep Read

Triggered by: *"generate deep-read"* or `python tools/deep-read.py --date YYYY-MM-DD`

Steps:
1. Read brief.md to find entries marked `[x] 深度阅读` and `[x] 不感兴趣`
2. For each `[x] 不感兴趣` entry, call LLM to generate interests.md update suggestions:
   - Suggest adding to 排除列表 or modifying existing interests
   - Save suggestions to `raw/digest/YYYY-MM-DD/disinterest-suggestions.md`
   - 控制台输出建议供参考
3. For each `[x] 深度阅读` entry, call LLM to generate 1500-3000 word deep-dive report:
   - Core viewpoints deep analysis
   - Technical/methodology breakdown
   - Key data/insights interpretation
   - Comparison with related fields
   - Potential issues/limitations
4. Save deep-dive reports to `raw/digest/YYYY-MM-DD/deepdive.md`

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

## Code Reading Workflow

Triggered by: *"read code"* or *"代码阅读"*

**核心原则**: 全流程由子代理完成，主 agent 仅负责 spawn，避免占用主 agent 上下文。

### 子代理工作流

1. **收集代码**: 运行 `python tools/code-read.py collect <path> [--url <git-url>]` 输出源码 JSON
2. **分析代码**: 子代理读取源码，用自身 LLM 能力生成结构化分析 JSON（含 title, slug, language, summary, framework_overview, algorithm_flow, step_breakdown, io_analysis, 3 张 Mermaid 图, dependencies, key_data_structures, design_patterns）
3. **写入 Wiki**: 运行 `python tools/code-read.py write --json-file <path>` 生成 wiki 页面 + 更新 index + log

### 主 agent 调用示例

```python
actor({
    "operation": "run",
    "subagent_type": "general",
    "description": "代码走读: <project-name>",
    "prompt": """分析代码并生成 wiki 页面。

步骤：
1. 运行 `python tools/code-read.py collect <path> [-o /tmp/code.json]` 收集代码
2. 读取源码，生成结构化分析 JSON（字段见下）
3. 将 JSON 写入 /tmp/analysis.json
4. 运行 `python tools/code-read.py write --json-file /tmp/analysis.json`

分析 JSON 必须包含：
- title: 简明标题
- slug: kebab-case 文件名
- language: 主要编程语言
- summary: 2-4 句概述
- framework_overview: 架构描述（300-500字）
- algorithm_flow: 核心算法流程（300-500字）
- step_breakdown: 步骤数组（step, name, input, process, output）
- io_analysis: 输入输出分析（200-400字）
- mermaid_architecture: Mermaid graph TD 架构图
- mermaid_flowchart: Mermaid flowchart LR 流程图
- mermaid_callgraph: Mermaid graph LR 调用图
- dependencies: 外部依赖数组
- key_data_structures: 数据结构描述（100-300字）
- design_patterns: 设计模式描述（100-200字）
- source_path: 源码路径
- source_url: 仓库地址（可选）

使用中文撰写所有描述。Mermaid 节点用中文标注。"""
})
```

### inbox 中的代码走读

inbox.py 检测到 git URL 或本地路径时，输出 `[code] <link> — 待子代理处理`。主 agent 应 spawn 子代理处理：

1. 读 `raw/inbox/inbox.md` 找 type=git/local 的条目
2. 对每个条目 spawn 子代理执行上述工作流
3. 清理 inbox.md 中已处理的行

---

## Ingest Workflow

Triggered by: *"ingest <file>"*

详细步骤见 [`docs/workflows/ingest.md`](docs/workflows/ingest.md)（含 Concept Distinction + Source-Type Templates）。

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

详细步骤见 [`docs/workflows/lint.md`](docs/workflows/lint.md)（含 interests.md Format）。

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

详细步骤见 [`docs/workflows/graph.md`](docs/workflows/graph.md)。

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
