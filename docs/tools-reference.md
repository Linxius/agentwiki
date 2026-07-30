# 工具速查

> 每个工具一行用途 + 输入/输出。详细 args 见各工具 `--help`。

## Pipeline 工具

| 工具 | 命令 | 读 | 写 | 一句话 |
|------|------|----|-----|--------|
| **feeds** | `python tools/feeds.py` | config.json | inbox.md | 从 arXiv API 拉取新论文链接 |
| **inbox** | `python tools/inbox.py` | inbox.md | `raw/inbox/YYYY-MM-DD/*.md` | 转换 inbox 链接为本地 .md 文件 |
| **filter** | `python tools/filter.py` | `raw/inbox/`, interests.md | `digest/brief.md`, `digest/sources/` | 筛选并生成简报 |
| **deep-read** | `python tools/deep-read.py` | brief.md, 源文件 | `digest/deepdive/YYYY-MM-DD/*.md` | 生成深度阅读报告 |
| **ingest** | `python tools/ingest.py` | brief.md, 源文件 | `wiki/sources/*.md`, index.md, log.md | 合入 wiki |
| **fetch-sources** | `python tools/fetch-sources.py` | brief.md | 源文件 | 抓取 brief 缺失的源文件 |

## Ingest 专有模式

| 模式 | 命令 | 说明 |
|------|------|------|
| Digest 合入 | `python tools/ingest.py --from-digest [YYYY-MM-DD]` | 从 brief 合入勾选条目 |
| 直接合入 | `python tools/ingest.py --paper <url-or-id>` | 跳过全部流程，URL/ID 直入 wiki |
| Phase 1 | `--phase1` | 写 prompt 到 `raw/.tmp/wiki-tasks/` |
| Phase 2 | `--phase2` | 读子代理结果继续处理 |
| 直接 LLM | `WIKI_LLM_DIRECT=1` | 写 prompt 到单文件，两步完成合入 |
| 重试失败 | `--retry-failed` | 重试结果为空或失败的 task |
| 清理 task | `--clean` | 显式清除 task/result 文件（默认保留） |

## Deep-read 专有模式

| 模式 | 命令 | 说明 |
|------|------|------|
| 直接阅读 | `--paper <url-or-path>` | 跳过 inbox，单篇论文生成报告 |
| 按文件 | `--file <filename>` | 处理 brief 中特定文件 |
| 按日期 | `--date YYYY-MM-DD` | 处理特定日期条目 |

## 维护工具

| 工具 | 命令 | LLM | 说明 |
|------|------|-----|------|
| **health** | `python tools/health.py` | ❌ | 结构完整性检查（空文件、索引同步）。自动修复 |
| **lint** | `python tools/lint.py` | ✅ | 内容质量检查（断链、缺失页面、矛盾） |
| **build-graph** | `python tools/build_graph.py` | ✅ | 构建知识图谱 JSON + HTML |
| **heal** | `python tools/heal.py` | ✅ | 自动补全缺失实体/概念页 |
| **refresh** | `python tools/refresh.py` | ✅ | 重新 ingest 已变更源文档 |

## 查询工具

| 工具 | 命令 | 说明 |
|------|------|------|
| **query** | `python tools/query.py` | 基于 wiki 内容回答问题 |

## 辅助工具

| 工具 | 说明 |
|------|------|
| **pdf2md.py** | PDF → Markdown 转换（非 arXiv PDF） |
| **file_to_md.py** | 通用文件 → Markdown |
| **download-images.py** | 下载文档中的图片 |
| **import-edge-bookmarks.py** | 从 Edge 书签导入链接到 inbox.md |
| **status.py** | 检查 pipeline 各节点状态 |
| **validate-wiki.py** | Wiki 链接有效性检查 |
| **sync-overview.py** | 同步 overview.md |
| **code-read.py** | 代码走读：collect → 分析 → write |

## 关键路径

```
# 完整流程
python tools/feeds.py                    # 拉取新论文
python tools/inbox.py                     # 转换链接
python tools/filter.py                    # 筛选 → brief.md
# agent 阅读 brief.md，确认勾选
python tools/deep-read.py                 # 生成深度阅读
python tools/ingest.py --from-digest      # 合入 wiki

# 快速流程（跳过中间步骤）
python tools/ingest.py --paper 2509.24421  # arXiv ID 直接合入

# 维护
python tools/health.py                     # 结构检查（零 LLM）
python tools/lint.py                       # 内容检查（需 LLM）
```
