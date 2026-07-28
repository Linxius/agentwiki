# LLM Wiki Agent — Schema & Workflow Instructions

> **先读 `docs/architecture.md`**（~100 行）快速了解项目结构和数据流。
> 需要时参考本文档（常驻概要）或 `docs/workflows/` 下的详细子文档。
> 工具速查见 `docs/tools-reference.md`。
> 项目优化相关见 `.opencode/skills/wiki-project-optimize/SKILL.md`。

## Output Language

`config.json` specifies `"output_language": "zh-CN"`. All wiki output must be written in Simplified Chinese.

This wiki is maintained entirely by your coding agent. No API key needed — just open this repo in any agent that reads this file, and talk to it.

## ⚠️ PDF Handling Rule

**NEVER use the Read tool on `.pdf` files.** Always run `python tools/pdf2md.py <file.pdf>` first, then `ingest` on the generated `.md` file。


## Trigger 速查

完整触发词表见 [`docs/workflows/triggers.md`](docs/workflows/triggers.md)。高频触发词：

| 触发词 | 动作 | 详情 |
|--------|------|------|
| `import bookmarks` / `导入书签` | 书签导入 → 去重 → 归档，然后 inbox.py 下载 + filter.py 简报 | [tools-reference.md](docs/tools-reference.md) |
| `filter` / `开始筛选` | 筛选 inbox/ → 生成 brief.md | [filter.md](docs/workflows/filter.md) |
| `deep read` / `生成深度阅读` | 对 brief 勾选条目生成报告 | [deep-read.md](docs/workflows/deep-read.md) |
| `ingest from digest` / `合入 wiki` | digest 勾选条目合入 wiki | [ingest.md](docs/workflows/ingest.md) |
| `ingest <file>` / `合入 <file>` | 直接合入单个文件 | [ingest.md](docs/workflows/ingest.md) |
| `read paper <url>` / `深度阅读 <url>` | 直接阅读并生成深度阅读 | [deep-read.md](docs/workflows/deep-read.md) |
| `ingest paper <url>` / `直接合入 <url>` | 直接下载并合入（跳过全部流程） | [ingest.md](docs/workflows/ingest.md) |
| `read code` / `代码阅读` | 子代理驱动代码分析 | [code-read.md](docs/workflows/code-read.md) |
| `status` / `流程状态` | 检查各节点进度并建议下一步 | — |
| `fetch sources` / `抓取源文件` | 抓取 brief 中缺失的源文件 | — |

Agent 主动提醒（完整列表见 `triggers.md` #Agent 主动提醒）：inbox 待处理、filter 待执行、deep-read 待生成、ingest 待合入、feeds 过期、源文件缺失。

## 流程优化

每次操作后自觉评估优化机会。原则见 [`docs/workflows/optimization.md`](docs/workflows/optimization.md)。

## Status Flow

`inbox.md 链接` → `inbox 处理（inbox/）` → `filter 筛选` → `brief 待确认` → `深度阅读 / 合入 wiki` → `已合入/已跳过`

每次用 `python tools/status.py` 检查当前阶段。依次检查：
1. **inbox.md 链接数** — 是否有未处理链接
2. **inbox/ 待筛选文件** — 是否有已转换但未筛选的文件
3. **brief 状态** — 简报是否已生成，是否有已勾选条目
4. **深度阅读 / 合入数量** — brief 中 `[x]` 勾选情况
5. **feeds 状态** — 各源上次拉取时间

---

## Directory Layout

```
raw/          inbox/  inbox.md  inbox/YYYY-MM-DD/*.md
              digest/  brief.md  deepdive/YYYY-MM-DD/  sources/YYYY-MM-DD/  brief/
              filter/ papers/ articles/ talks/ books/ projects/ docs/ datasets/
              codes/   .tmp/
wiki/         index.md log.md overview.md issues.md interests.md
              sources/ entities/ concepts/ syntheses/
graph/        graph.json graph.html
templates/    generic.md paper.md article.md book.md dataset.md doc.md project.md talk.md
tools/        inbox.py filter.py deep-read.py ingest.py status.py health.py lint.py \
              import-edge-bookmarks.py bookmark-tracker.py ...
```

## Workflows Overview

所有流程的详细步骤均在 `docs/workflows/` 下。

| 流程 | 入口 | 位置 |
|------|------|------|
| Filter（筛选） | `filter` | [docs/workflows/filter.md](docs/workflows/filter.md) |
| Deep Read（深度阅读） | `deep read` | [docs/workflows/deep-read.md](docs/workflows/deep-read.md) |
| Ingest（合入） | `ingest` / `ingest from digest` | [docs/workflows/ingest.md](docs/workflows/ingest.md) |
| Code Reading（代码走读） | `read code` | [docs/workflows/code-read.md](docs/workflows/code-read.md) |
| Lint（内容质检） | `lint` | [docs/workflows/lint.md](docs/workflows/lint.md) |
| Health（结构检查） | `health` | 直接运行 `python tools/health.py` |
| Graph（知识图谱） | `build graph` | [docs/workflows/graph.md](docs/workflows/graph.md) |
| Query（问答） | `query: <question>` | 读 wiki/index.md → 读对应页面 → 合成回答 |

## Page Format

**所有 wiki 页面必须遵循 `templates/` 中的对应模板。** 可用模板：`paper.md`、`article.md`、`book.md`、`dataset.md`、`doc.md`、`project.md`、`talk.md`、`generic.md`。

Paper 模板结构：Summary → 原始出处 → Key Contributions → Method(框架图+双重写作) → Training → Results & Comparisons → Related Work Analysis → Ablations → Limitations → 评论与启示 → Connections → Contradictions。

图片引用：`![描述](https://arxiv.org/html/.../figures/images/...)`（arxiv 直链）或 `![描述](../images/<slug>/文件名)`（本地）。

使用 `[[PageName]]` wikilinks 链接其他 wiki 页面。

---

## Naming Conventions

- Source slugs: `kebab-case` 匹配源文件名
- Entity/Concept pages: `TitleCase.md`（如 `OpenAI.md`、`ReinforcementLearning.md`）

## Index & Log Format

Index: `## {Section}\n- [Title](path) — one-line`。见 `wiki/index.md`。
Log: `## [YYYY-MM-DD] <operation> \| <title>`。操作：`ingest`, `query`, `health`, `lint`, `graph`, `report`。日期使用操作执行日期。

---

## Reply Style

Respond in Chinese with minimal, technical text. No pleasantries, no openings, no summaries. Use newlines and short paragraphs for clarity. This rule applies to text responses only; code, comments, and commit messages remain as usual.
