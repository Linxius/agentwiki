# Wiki Pipeline 待优化清单

> 优先级：P0（数据安全/阻塞）> P1（流程缺陷）> P2（效率/质量）

---

## 已完成 ✓

### P0 修复
- [x] **`call_llm()` 不崩溃** → 改为自动创建 task 文件（phase1）返回空字符串，不再 `sys.exit(1)`. `auto_call_or_phase1()` 辅助函数
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
- [x] **`overview_update` 全量替换设计缺陷** → `ingest.py` 改为 `_append_to_overview()` 追加模式，不再依赖子代理返回完整内容
- [x] **`--paper` 模式重复 fetch** → `_refetch_arxiv` 增加 429 重试 + webfetch HTML 降级 + 检查已有源文件
- [x] **子代理结果协议不匹配** → `read_results()` 同时支持 `.txt` + `.json`（均需 `.done` 标记）；`read_result()` 同理
- [x] **`ingest.py` `_SHARED_CONTEXT_PATH` 未初始化** → 已修复

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
- [x] **arxiv2md 429 无重试** → `_refetch_arxiv` 增加指数退避重试（3 次）+ arxiv HTML webfetch 降级
- [x] **子代理 prompt 过大导致指令遗漏** → 源文件 >20KB 时不内联，子代理自行 Read
- [x] **`RESULT_DIR` 自动创建缺失** → `read_results()` 中增加自动创建
- [x] **削减脚本 print 输出** → `ingest.py` 126→45 个 print（仅保留错误/CLI 帮助），`_utils.py` 5→0

---

## 待处理

### P0: arxiv2md 下载数据安全

**问题**：`arxiv2md -o <filename>` 把 filename 当作**目录**创建，实际文件放在 `<filename>/<paper-title>.md` 内。

**已修复**：
- [x] **封装 `safe_download_arxiv(arxiv_id, out_path)`** 到 `_utils.py`：传递目录给 `-o`，glob 找文件，验证长度 ≥5000，rename 到目标路径；CLI 失败时 fallback 到 Python API
- [x] **修复 `pdf2md.py:convert_arxiv()`**：改用 `safe_download_arxiv`，不再直接 `-o <file>`
- [x] **`inbox.py:fetch_arxiv()`** 已使用正确模式（目录传参 + glob），无需修改
- [x] **仍有 `-o` 直接传文件的其他调用点？确认只有 pdf2md.py 一处** → 已确认，无其他遗留

### P1: `ingest.py raw/digest` 误用

**问题**：`ingest.py raw/digest` 递归找到所有 .md 文件，不解析复选框。

**已修复**：
- [x] **输入检测**：检测到 `digest` 在路径中时弹出警告，建议使用 `--from-digest`

### P1: `run_from_digest` 源文件缺失时自动下载

**问题**：brief 标记条目引用的源文件可能不存在。

**已修复**：
- [x] **自动下载**：`run_from_digest` 检测到源文件缺失时，从 `source_url` 提取 arxiv ID 调用 `safe_download_arxiv`
- [x] **`--no-auto-fetch` 标志**：`ingest.py --from-digest --no-auto-fetch` 可选关闭

### P1: 归档前备份 + 未标记条目保护

**已修复**：
- [x] **按条目逐个移除**：每成功 ingest 一个条目，立即从 brief.md 移除该条目，其余不动
- [x] **`brief.md.orig`**：已加入 `.gitignore` 并删除（brief 已归档，备份过时）
- [x] 不需要 `run_archive()` 整体归档

### P2: 两阶段协议自动化

**问题**：当前 agent 需手动 spawn 子代理处理 task 文件，然后再跑 phase2。

**已修复**：
- [x] **`--auto` 标志**：`ingest.py --from-digest --auto` 自动 phase1 → 等待子代理 → phase2
- [x] **`run_phase_auto()`** 函数在 `_utils.py`：阻塞等待所有 task 的 `.done` 标记后自动执行 phase2

### P2: 重复下载优化

**问题**：同一论文在不同流程中可能被多次下载。

**已修复**：
- [x] **arxiv 缓存**：`safe_download_arxiv()` 写入 `raw/.tmp/arxiv-cache/<arxiv_id>/<arxiv_id>.md`，下次下载直接读取

---

## 后续触发词速查

| 你想... | 说 |
|--------|-----|
| 加载项目优化 skill | `load wiki optimize skill` |
| 外部化 AGENTS.md 更多内容 | `externalize agents content` |
