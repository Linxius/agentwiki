# Filter Workflow

> 从 AGENTS.md 外部化以节省常驻 token。执行 filter 操作时阅读此文。

Triggered by: *"filter"* or `python tools/filter.py`

## 推荐工作流（批量子代理 + --build-brief）

Steps:
1. Scan `raw/inbox/` for files
2. Read `wiki/interests.md`（含 `## 兴趣列表` 和 `## 排除列表` 两个分区；排除列表按 `### 方向/细分领域/技术` 分层组织）
3. Main agent 读取所有文件紧凑预览（只取 title + abstract，~2500 chars 每文件）
4. 按 10-15 个文件一批，spawn 子代理并行分析。**不要每个文件一个子代理。**
   - 每个子代理共享 prompt 模版（兴趣列表、匹配规则）
   - 子代理返回 JSON 数组，包含 `brief`、`detailed_report`、`match_level` 等
   - **必须提供 `figure_url` 和中文 `figure_caption`**（框架图URL和中文说明）
5. 收集所有结果到 `results.json`
6. 运行 `python tools/filter.py --build-brief results.json`
   - 自动从源文件提取框架图URL和完整描述
   - 自动生成中文 alt text 的 `![描述](url)` 图片标签
   - 归档旧 brief → `raw/digest/brief/YYYY-MM-DD.md`
   - 生成新 `raw/digest/brief.md`
   - 移动源文件到 `raw/digest/sources/YYYY-MM-DD/`
   - 清空 `raw/inbox/`
7. 控制台汇总 LLM 建议的新增兴趣/排除项供参考

**旧工作流（废弃）：** `--phase1/--phase2` 文件传输协议。不再使用。

## ⚠️ 兴趣匹配规则（保守原则）

- **只标记 `interested` 当文档核心主题与兴趣条目直接对应**。关键词只是辅助，不能仅凭关键词出现就判定感兴趣
- **`possibly_interested` 要求：** 文档至少 30% 内容与兴趣条目相关，而非仅提及
- **宁可漏判不可误判**：拿不准时标记 `not_interested`，让用户在 brief 中手动发现
- **不要发散猜测**：不要因为标题/摘要提到了兴趣领域的上位概念就标记感兴趣（如兴趣是"3D高斯泼溅"，不要因为文档提到"3D视觉"就标记）
- **匹配理由必须具体**：写明"文档的 XXX 部分直接讨论了 XXX 兴趣条目"，而非"文档涉及相关领域"

## ⚠️ brief.md 源文件自动抓取

当 brief.md 中条目的源文件路径对应文件为空（0 字节）或不存在时，自动从 `source_url` 重新抓取内容：
- arxiv URL → `arxiv2md <arxiv_id> -o <path>`
- 网页 URL → `webfetch` + trafilatura 提取
- PDF → `python tools/pdf2md.py <url> -o <path>`
- 抓取后更新 brief.md 中对应条目的源文件路径
