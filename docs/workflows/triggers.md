# Trigger 速查表

> 从 AGENTS.md 外部化以节省 token。需要时引用此文。

## Pipeline 触发词

| 说 | agent 做 |
|----|----------|
| `feeds` / `拉取 feeds` | 从配置源拉取新内容到 inbox/ |
| `inbox` / `处理 inbox` | 解析 inbox.md 链接 → 生成 .md |
| `import bookmarks` / `导入书签` | 从 Edge 书签导入链接到 inbox.md |
| `dedup inbox` / `去重 inbox` | 按 arxiv ID 去重 |
| `archive bookmarks` / `归档书签` | Edge 书签移入 Wiki/Inbox Archive |
| `书签流程` / `bookmark pipeline` | 导入 → 去重 → 归档 |
| `filter` / `开始筛选` | 筛选 inbox/ → 生成 brief.md |
| `deep read` / `生成深度阅读` | 对 brief 中勾选的条目生成报告 |
| `合入 wiki` / `ingest from digest` | digest 勾选条目合入 wiki |
| `ingest <file>` / `合入 <file>` | 直接合入单个文件 |
| `read paper <url>` / `深度阅读 <url>` | 直接阅读并生成深度阅读 |
| `ingest paper <url>` / `直接合入 <url>` | 下载 → 直接合入 wiki（跳过全部流程） |
| `read code` / `代码阅读` | 子代理驱动代码分析 |
| `search papers <query>` / `搜索论文` | alphaXiv MCP 搜索 |
| `status` / `流程状态` | 检查各节点进度 |
| `fetch sources` / `抓取源文件` | 抓取 brief 中缺失的源文件 |

## 维护触发词

| 说 | agent 做 |
|----|----------|
| `health` | 结构完整性检查（零 LLM） |
| `lint` | 内容质量检查（需 LLM） |
| `build graph` | 构建知识图谱 |
| `heal` | 补全缺失实体/概念页 |
| `refresh` | 重新 ingest 已变更源文档 |

## 查询触发词

| 说 | agent 做 |
|----|----------|
| `query: <question>` | 基于 wiki 内容回答 |
| `read paper <arxiv_id>` | arxiv2md + LLM 深度阅读 |

## Agent 主动提醒

| 条件 | agent 说 |
|------|----------|
| inbox.md 有链接 | "inbox.md 中有 N 个链接待处理" |
| inbox/ 有文件 | "今日有 N 份文件待筛选" |
| brief 有勾选但未深读 | "brief.md 有 [x] 深度阅读 但未生成报告" |
| brief 有勾选但未合入 | "brief.md 有 [x] 合入 wiki 但未处理" |
| feeds 过期 | "feeds 已 N 天未拉取" |
| 源文件缺失 | "brief.md 有 N 个源文件为空/缺失" |
