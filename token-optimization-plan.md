# Token 消耗全局优化方案

## 现状

| 维度 | 当前值 | 问题 |
|------|--------|------|
| AGENTS.md 本身 | **8,407 tokens** | 每次 session 固定加载 |
| ingest.py 兴趣提取 | **75-90 KB/次**（内联 AGENTS.md） | 已有共享上下文机制但未用于此路径 |
| query.py 综合回答 | **70-150 KB/次**（内联 AGENTS.md） | 同上 |
| code-read 子代理 prompt | 内联在 AGENTS.md 中（~2,174 tokens） | 文档性质，主 agent 从不执行它 |

## 目标

- AGENTS.md: ~8,400 → **~4,500 tokens**（保守，核心指令不丢失）
- Pipeline 运行时: 每次 LLM 调用节省 **~67 KB**（不内联 AGENTS.md 全文）

---

## A. AGENTS.md 瘦身（-3,500 tokens）

### A1. 移除内联 Python 代码块（-1,500 tokens）
- **范围**: L363-505（`actor()` 调用示例 + 子代理 prompt 模板）
- **去向**: 新建 `docs/workflows/code-read.md`，存放完整 prompt 模板
- **AGENTS.md 保留**: 一行引用 + 关键约束
  ```
  ### 子代理工作流
  子代理 prompt 模板见 `docs/workflows/code-read.md`。
  必须包含: 3 张 Mermaid 图、双重写作、中文撰写。
  ```

### A2. 合并 Trigger 表格（-400 tokens）
- **当前**: 3 张独立表格（Pipeline 19 行、Maintenance 7 行、Query 5 行）
- **优化**: 合并为 1 张单列表（`触发词 → 动作`），去除重复的 `|---|` 分隔线

### A3. 精简 alphaXiv MCP 章节（-200 tokens）
- **移除**: 工具表（L14-19，已存在于 docs/setup.md）
- **移除**: 安装命令（L31，已存在于 docs/setup.md）
- **移除**: 示例代码块（L33-40）
- **保留**: 仅关键警告「不要用 get_paper_content 获取全文」+ 正确流程（arxiv2md + answer_pdf_queries）

### A4. 精简 Page Format 章节（-300 tokens）
- **移除**: 完整的 Paper 模板 YAML 块 + 章节列表（L298-327，已存在于 templates/paper.md）
- **保留**: 3 条关键约束（Method 章节放框架图、双重写作、`[[wikilinks]]`）

### A5. 外部化 Workflow 详细步骤（-600 tokens）
- **Filter 流程**: L181-197 的 6 步 → 精简为 3 条要点 + 引用 `docs/workflows/` 或 trust script
- **Deep Read 流程**: L222-233 的 4 步 → 精简为要点
- **Ingest 流程**: L265-274 的 7 步 → 精简为要点 + 引用 `docs/workflows/ingest.md`
- **其余 workflow (Graph/Health/Lint)**: L518-596 已引用 docs/ 文件，缩小节标题 + 移除重复表格

### A6. 精简 Workflow Optimizations（-150 tokens）
- **移除**: 节省原则表（L110-117），保留 prose 版本（L102-108）+ 提示方式（L119）

### A7. 精简 Agent Proactive Reminders（-150 tokens）
- L91-98: 7 条列表 → 3 条要点（inbox.md 待处理、filter 待运行、brief 待确认）

### A8. 其他小缩减（-200 tokens）
- Status Flow 细节（L131-137）→ status.py 已处理，移除
- Directory Layout（L143-158）→ 保留关键路径
- Pre-step Inbox Links 步骤 → 精简

---

## B. Pipeline 运行时优化（每次 LLM 调用节省 ~67 KB）

### B1. ingest.py 兴趣提取复用共享上下文（-68 KB/次）
- **当前**: `build_interest_extraction_prompt()` 内联完整 AGENTS.md（L220-229）
- **修改**: 复用 `get_shared_ingest_context()` 的缓存文件路径，prompt 中替换为文件引用
- **文件**: `tools/ingest.py` L198-255

### B2. query.py 使用精简 Schema（-67 KB/次）
- **当前**: `build_synthesis_prompt()` 内联完整 AGENTS.md（L96-108）
- **修改**: 从 AGENTS.md 提取 3-5 条关键规则（~200 chars），或引用共享上下文文件
- **文件**: `tools/query.py` L96-108

### B3. build_graph.py / lint.py 修复 SCHEMA_FILE 引用
- **当前**: SCHEMA_FILE 指向不存在的 `CLAUDE.md`（无实际效果）
- **修改**: 改为指向 `AGENTS.md` 并使用共享上下文模式，或直接使用精简 schema
- **影响**: 当前不消耗 token（文件不存在），修复后也不应增加消耗

---

## C. 新建文件

### `docs/workflows/code-read.md`
存放原 AGENTS.md L363-505 的完整子代理 prompt 模板，包括：
- 分析 JSON 字段定义
- Mermaid 图规范（architecture/flowchart/callgraph）
- flowchart_details 写作要求
- Wiki 页面结构规范

### `docs/workflows/paper-template.md`（可选）
存放原 AGENTS.md L298-327 的 Paper 模板 Frontmatter + 章节结构说明

---

## D. 验证方法

1. **AGENTS.md token 数**: `python -c "import tiktoken; enc=tiktoken.encoding_for_model('gpt-4'); print(len(enc.encode(open('AGENTS.md').read())))"` 应 < 5000
2. **Pipeline prompt 大小**: 在 `build_*_prompt()` 函数返回前加 `print(len(prompt))` 查看实际大小
3. **功能完整性**: 
   - 运行 `python tools/status.py` 确认工具仍可正常工作
   - 发送 `inbox` / `filter` / `deep read` / `合入 wiki` 等触发词确认 agent 正确响应
4. **引用完整性**: `grep -n "docs/workflows/" AGENTS.md` 确认所有外部引用路径正确
