# Wiki Pipeline 已完成优化归档

> 已完成、已归档的优化记录。当前待处理见 [TODO.md](TODO.md)。

---

## [2026-07-30] Phase1→Phase2 协议、auto 模式、缓存等

### P0: `call_llm()` 不崩溃
→ 改为自动创建 task 文件（phase1）返回空字符串，不再 `sys.exit(1)`. `auto_call_or_phase1()` 辅助函数

### P0: RESULT_DIR 自动创建
→ `prepare_tasks()` 中增加 `RESULT_DIR.mkdir()`

### P0: 子代理写入同步机制
→ `write_result()` 写 `.done` 标记；`read_results()` 只读有 `.done` 的结果；`wait_for_tasks()` 轮询函数

### P0: TASK/RESULT_DIR 从 `/tmp/` 移到 `raw/.tmp/`
→ `_utils.py`

### P0: `run_from_digest` move→copy2 源文件生命周期
→ `ingest.py`

### P0: `input()` 全面 `isatty` 保护
→ `ingest.py`

### P1: filter.py 归档日期
→ `archive_current_brief()` 从 brief header 提取日期，不再 `date.today()`. `generate_new_brief()` 复用归档日期

### P1: 源文件命名用论文名
→ `title_to_slug()` + `rename_file_by_title()` 在 `_utils.py`；`_refetch_arxiv()` / `_refetch_web()` 在 deep-read.py 和 ingest.py 中转换后自动重命名

### P1: 深度阅读章节标题清除 prompt 指令
→ `clean_report_section_titles()` 后处理，用 regex 去掉 `（仅背景...）` 类括号说明

### P1: 深度阅读元数据
→ `deep-read.py` prompt 注入 source_url、brief 引用等元数据区块

### P1: 深度阅读双结构
→ prompt 要求"整体思路 + 分步拆解"双重写作

### P1: 评论/启示写入 wiki
→ `ingest.py` 传递 comments→prompt；模板新增 `## 评论与启示` 章节；AGENTS.md 说明 agent 行为

### P1: Wiki 页面源文件引用
→ 模板 `## 原始出处` 增加 brief/deepdive 引用行

### P1: 直接合入功能
→ `ingest.py` 新增 `--paper <url-or-id>` 模式

### P1: 深读 phase1 同时处理不感兴趣+深读
→ 合并 task 列表，不再中途 return

### P1: 共享上下文缓存失效
→ marker 文件 + mtime 检查，`prepare_tasks()` 时自动刷新

### P1: deep-read 普通模式自动转 phase1
→ 不再走废弃 `call_llm` 路径

### P1: deep-read.py `--file` 模式
→ 因 `call_llm()` 不再崩溃而自然修复

### P1: `build_brief_from_json` 日期统一
→ `filter.py`

### P1: `fetch-sources.py` 解析只处理 `####` 条目 + 支持 `--all` 批量

### P1: deep-read.py 各种修复
→ 归档日期、图片 cleanup、TASK_DIR 导入、dedup 检查

### P1: `overview_update` 全量替换设计缺陷
→ `ingest.py` 改为 `_append_to_overview()` 追加模式，不再依赖子代理返回完整内容

### P1: `--paper` 模式重复 fetch
→ `_refetch_arxiv` 增加 429 重试 + webfetch HTML 降级 + 检查已有源文件

### P1: 子代理结果协议不匹配
→ `read_results()` 同时支持 `.txt` + `.json`（均需 `.done` 标记）；`read_result()` 同理

### P1: `ingest.py` `_SHARED_CONTEXT_PATH` 未初始化
→ 已修复

### P2: AGENTS.md 瘦身
→ code-read 子代理模板（~200 行）外部化至 `docs/workflows/code-read.md`；trigger 表格外部化至 `docs/workflows/triggers.md`. 省 ~2500-3500 token/session

### P2: SCHEMA_FILE 统一
→ `build_graph.py` / `lint.py` / `query.py` 指向 `CLAUDE.md` → 改为 `AGENTS.md`

### P2: 前置阅读优化
→ AGENTS.md 顶部"先读 docs/architecture.md"指引

### P2: 项目速查文档
→ `docs/architecture.md` + `docs/tools-reference.md`

### P2: 项目优化 skill
→ `.opencode/skills/wiki-project-optimize/SKILL.md`

### P2: 子代理 prompt 过大
→ 策略文档化：每子代理 1 论文；共享 context 避免内联 schema

### P2: 子代理输出格式
→ prompt 末尾加"直接输出纯文本，不要 ```markdown ``` 包裹"指令

### P2: 子代理自恢复不一致
→ protocol 已保证 phase1 准备所有数据，子代理不应 fallback

### P2: `deepdive.md` 索引消失
→ phase1 dedup 增加 fallback：deepdive.md 不存在但单独文件存在也视为已处理

### P2: filter 建议合入
→ `_apply_suggestions()` 函数 + `--apply-suggestions` 参数

### P2: 共享上下文文件缓存
→ `ingest.py` `get_shared_ingest_context()`, 省 ~68KB/task

### P2: 深度阅读源文件定位 + 输出路径 + 图片引用
→ 多目录搜索、`{slug}.md` 独立文件、`images/` 子目录

### P2: 概览/技术拆解重叠 + 图片选择 prompt
→ 重写

### P2: arxiv2md 429 无重试
→ `_refetch_arxiv` 增加指数退避重试（3 次）+ arxiv HTML webfetch 降级

### P2: 子代理 prompt 过大导致指令遗漏
→ 源文件 >20KB 时不内联，子代理自行 Read

### P2: `RESULT_DIR` 自动创建缺失
→ `read_results()` 中增加自动创建

### P2: 削减脚本 print 输出
→ `ingest.py` 126→45 个 print（仅保留错误/CLI 帮助），`_utils.py` 5→0

---

## [早期] arxiv2md 下载数据安全

- `safe_download_arxiv(arxiv_id, out_path)` 到 `_utils.py`
- `pdf2md.py:convert_arxiv()` 改用 `safe_download_arxiv`
- 确认无其他遗留 `-o` 直接传文件调用点

## [早期] `ingest.py raw/digest` 误用
→ 输入检测弹出警告，建议使用 `--from-digest`

## [早期] `run_from_digest` 源文件缺失时自动下载
→ `safe_download_arxiv` 自动获取 + `--no-auto-fetch` 标志

## [早期] 归档前备份 + 未标记条目保护
→ 按条目逐个移除；`brief.md.orig` 加入 `.gitignore`

## [早期] 两阶段协议自动化
→ `--auto` 标志 + `run_phase_auto()` 函数

## [早期] 重复下载优化
→ arxiv 缓存到 `raw/.tmp/arxiv-cache/<arxiv_id>/`
