# Wiki Pipeline 待优化清单

> 优先级：P0（阻塞/数据安全）> P1（流程缺陷）> P2（效率/质量）
>
> 所有 P0、P1 问题已处理完成。

---

## 已完成 ✓

### P0 修复
- [x] **`call_llm()` 不崩溃** → 改为自动创建 task 文件（phase1）返回空字符串，不再 `sys.exit(1)`。附带 `auto_call_or_phase1()` 辅助函数
- [x] **RESULT_DIR 自动创建** → `prepare_tasks()` 中增加 `RESULT_DIR.mkdir()`
- [x] **子代理写入同步机制** → `write_result()` 写 `.done` 标记；`read_results()` 只读有 `.done` 的结果；`wait_for_tasks()` 轮询函数
- [x] **TASK/RESULT_DIR 从 `/tmp/` 移到 `raw/.tmp/`** → `_utils.py`
- [x] **`run_from_digest` move→copy2 源文件生命周期** → `ingest.py`
- [x] **`input()` 全面 `isatty` 保护** → `ingest.py`

### P1 修复
- [x] **filter.py 归档日期** → `archive_current_brief()` 从 brief header 提取日期，不再 `date.today()`. `generate_new_brief()` 复用归档日期
- [x] **源文件命名用论文名** → `title_to_slug()` + `rename_file_by_title()` 在 `_utils.py`；`_refetch_arxiv()` / `_refetch_web()` 在 deep-read.py 和 ingest.py 中转换后自动重命名
- [x] **深度阅读章节标题清除 prompt 指令** → `clean_report_section_titles()` 后处理，用 regex 去掉 `（仅背景...）` 类括号说明
- [x] **深度阅读元数据** → `deep-read.py` prompt 注入 source_url、brief 引用等元数据区块
- [x] **深度阅读双结构** → prompt 要求"整体思路 + 分步拆解"双重写作
- [x] **评论/启示写入 wiki** → `ingest.py` 传递 comments→prompt；模板新增 `## 评论与启示` 章节；AGENTS.md 说明 agent 行为
- [x] **Wiki 页面源文件引用** → 模板 `## 原始出处` 增加 brief/deepdive 引用行
- [x] **直接合入功能** → `ingest.py` 新增 `--paper <url-or-id>` 模式
- [x] **深读 phase1 同时处理不感兴趣+深读** → 合并 task 列表，不再中途 return
- [x] **共享上下文缓存失效** → marker 文件 + mtime 检查，`prepare_tasks()` 时自动刷新
- [x] **deep-read 普通模式自动转 phase1** → 不再走废弃 `call_llm` 路径
- [x] **deep-read.py `--file` 模式** → 因 `call_llm()` 不再崩溃而自然修复
- [x] **`build_brief_from_json` 日期统一** → `filter.py`
- [x] **`fetch-sources.py` 解析只处理 `####` 条目** + 支持 `--all` 批量
- [x] **deep-read.py 各种修复** → 归档日期、图片 cleanup、TASK_DIR 导入、dedup 检查

### P2 修复
- [x] **AGENTS.md 瘦身** → code-read 子代理模板（~200 行）外部化至 `docs/workflows/code-read.md`；trigger 表格外部化至 `docs/workflows/triggers.md`. 省 ~2500-3500 token/session
- [x] **SCHEMA_FILE 统一** → `build_graph.py` / `lint.py` / `query.py` 指向 `CLAUDE.md` → 改为 `AGENTS.md`
- [x] **前置阅读优化** → AGENTS.md 顶部"先读 docs/architecture.md"指引
- [x] **项目速查文档** → `docs/architecture.md` + `docs/tools-reference.md`
- [x] **项目优化 skill** → `.opencode/skills/wiki-project-optimize/SKILL.md`
- [x] **子代理 prompt 过大** → 策略文档化：每子代理 1 论文；共享 context 避免内联 schema
- [x] **子代理输出格式** → prompt 末尾加"直接输出纯文本，不要 ```markdown ``` 包裹"指令
- [x] **子代理自恢复不一致** → protocol 已保证 phase1 准备所有数据，子代理不应 fallback
- [x] **`deepdive.md` 索引消失** → phase1 dedup 增加 fallback：deepdive.md 不存在但单独文件存在也视为已处理
- [x] **filter 建议合入** → `_apply_suggestions()` 函数 + `--apply-suggestions` 参数
- [x] **共享上下文文件缓存** → `ingest.py` `get_shared_ingest_context()`, 省 ~68KB/task
- [x] **深度阅读源文件定位 + 输出路径 + 图片引用** → 多目录搜索、`{slug}.md` 独立文件、`images/` 子目录
- [x] **概览/技术拆解重叠 + 图片选择 prompt** → 重写

---

## 后续触发词速查

| 你想... | 说 |
|--------|-----|
| 加载项目优化 skill | `load wiki optimize skill` |
| 外部化 AGENTS.md 更多内容 | `externalize agents content` |
