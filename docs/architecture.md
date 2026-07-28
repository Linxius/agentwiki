# Wiki 项目架构

> 快速了解项目结构、数据流和关键模式。阅读此文档后无需再读 AGENTS.md 全文。

## 核心目标

维护一个学术知识 wiki：从 arXiv/网页/PDF 拉取内容 → 筛选 → 深度阅读 → 合入 wiki 页面。全程由 agent 驱动。

## 目录布局

```
raw/                  # 原始素材
  inbox/inbox.md      # 待处理的 URL 链接列表
  inbox/YYYY-MM-DD/   # 转换后的 .md 文件（临时）
  digest/brief.md     # 当前简报（筛选结果，含勾选框）
  digest/sources/     # 简报引用的源文件（按日期归档）
  digest/deepdive/    # 深度阅读报告（按日期归档）
  filter/papers|articles|.../  # 已分类的原始 .md（ingest 后移入）
  codes/              # git clone 的代码仓库
  .tmp/               # 中间产物（task 文件、缓存、临时脚本）
wiki/                 # 知识库输出
  index.md            # 页面索引
  log.md              # 操作日志（最新在最前）
  overview.md         # 综合概述
  sources/            # wiki 源页面
  entities/           # 实体页面（人、机构）
  concepts/           # 概念页面（技术术语）
  images/             # 图片资源
  syntheses/          # 综合问答页面
  interests.md        # 用户兴趣配置
templates/            # wiki 页面模板（paper.md, article.md 等）
tools/                # Python 工具脚本
docs/                 # 文档
graph/                # 知识图谱
```

## Pipeline 流程

```
inbox.md 链接 ─→ inbox (转换) ─→ filter (筛选) ─→ brief.md (确认) ─→ deep-read (深度阅读) ─→ ingest (合入) → wiki 页面
                     │                              │                       │
                     ↓                              ↓                       ↓
              raw/inbox/YYYY-MM-DD/          digest/sources/          digest/deepdive/YYYY/
```

### 阶段 0：Feeds
`python tools/feeds.py` — 从 arXiv API 拉取新论文链接，追加到 `inbox.md`。

### 阶段 1：Inbox 处理
`python tools/inbox.py` — 解析 `inbox.md` 中的 URL。arXiv 用 `arxiv2md`，网页用 `trafilatura`，转换后存 `raw/inbox/YYYY-MM-DD/`。

### 阶段 2：Filter 筛选
`python tools/filter.py` — 读取 `raw/inbox/` 文件，对比 `wiki/interests.md` 兴趣配置，生成 `digest/brief.md`。
- 子代理批量分析（每 10-15 个文件一批）
- 输出 JSON → `--build-brief` 生成 brief.md
- 源文件自动移动至 `digest/sources/YYYY-MM-DD/`

### 阶段 3：Deep Read 深度阅读
`python tools/deep-read.py` — 读取 `brief.md` 中勾选的条目，生成深度分析报告。
- `[x] 深度阅读` → 生成 1500-3000 字报告
- `[x] 不感兴趣` → 生成 interests.md 更新建议
- 输出到 `digest/deepdive/YYYY-MM-DD/{slug}.md`
- Direct read 模式：`--paper <url>` 跳过 inbox/filter

### 阶段 4：Ingest 合入
`python tools/ingest.py` — 读取 `brief.md` 中 `[x] 合入 wiki` 条目 → LLM 生成 wiki 页面。
- Direct ingest 模式：`--paper <url-or-id>` 跳过全部前置流程
- 源文件链接使用 `os.path.relpath()` 确保相对路径正确

## 关键数据文件格式

### brief.md 条目
```markdown
#### Paper Title
- 来源: https://arxiv.org/abs/XXXX.XXXXX
- 源文件: [raw/digest/sources/YYYY-MM-DD/slug.md](path)
- 领域: 3D重建
- 关键词: 3DGS, 实时渲染
- 匹配: 3D高斯泼溅
- 理由: ...
- [ ] 深度阅读
- [x] 合入 wiki
- [ ] 不感兴趣

![框架图](url)
**简介**：一句话摘要
**详细报告**：一段话分析
```

### wiki 页面 frontmatter
```yaml
---
title: "Paper Title"
type: source
tags: [paper]
date: YYYY-MM-DD
source_file: raw/papers/...
url: "https://arxiv.org/abs/XXXX"
venue: ""
published: YYYY
links: []
---
```

## Phase 1/2 子代理协议

子代理无法直接调用 LLM，通过文件系统通信：

1. **Phase 1** (主 agent 运行): 脚本写 prompt 到 `raw/.tmp/wiki-tasks/<id>.json` + manifest.json
2. **子代理** (agent spawn): 读取 task JSON，执行 LLM 推理，写结果到 `raw/.tmp/wiki-results/<id>.txt`
3. **Phase 2** (主 agent 运行): 脚本读取结果，继续处理

## 关键设计模式

| 模式 | 说明 |
|------|------|
| **Shared Context** | Schema 和 wiki 状态写入 `raw/.tmp/wiki-ingest-context.md`，子代理 `read` 而非内联（省 ~68KB/task） |
| **评论/启示传递** | Brief 评论、deep-read 启示、用户消息 → ingest 时自动写入 wiki `## 评论与启示` 章节 |
| **路径安全** | 所有链接用 `os.path.relpath()` 基于 repo 根计算，不硬编码日期或路径 |
| **去重** | brief 归档用 MD5 哈希避免重复追加；deep-read 用标题匹配跳过已处理条目 |
| **紧凑预览** | Filter 时只取 title+abstract (~2500 chars)，不读全文 |

## 配置

`config.json` — `output_language: "zh-CN"`, `feeds.sources` 定义 RSS/arXiv 源。

## 快速速查

| 问题 | 答案 |
|------|------|
| 数据从哪来？ | arXiv API (feeds), 手动添加 URL 到 inbox.md |
| 怎么定义兴趣？ | `wiki/interests.md` — `## 兴趣列表` + `## 排除列表` |
| 子代理找不到文件？ | 检查 `raw/.tmp/wiki-tasks/` 和 `raw/.tmp/wiki-results/` |
| 如何处理 PDF？ | `arxiv2md` (arXiv) 或 `tools/pdf2md.py` (非 arXiv) |
| 模板在哪？ | `templates/paper.md`, `templates/article.md` 等 |
| 日志在哪？ | `wiki/log.md` (反向时间序) |
| 健康检查？ | `python tools/health.py` (零 LLM) |
| 内容检查？ | `python tools/lint.py` (需 LLM) |
