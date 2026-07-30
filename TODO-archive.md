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

---

## [2026-07-31] 批量修复 r2

涉及文件：`_utils.py`、`ingest.py`、`deep-read.py`、`feeds.py`、`query.py`、`build_graph.py`、`refresh.py`

### P0: `call_llm()` 永远不调用 LLM
→ 新增 `WIKI_LLM_DIRECT=1` 环境变量模式：写 prompt 到 `raw/.tmp/wiki-llm-prompt.md`，agent 处理后将响应写入 `raw/.tmp/wiki-llm-response.md`，重新运行命令即可读取。保留默认 phase1 task 文件模式。
→ 修复受影响调用者（`deep-read.py`、`ingest.py`）处理空响应的逻辑

### P0: `--from-digest` 隐含追加 `--phase1`
→ 移除 `ingest.py:1695-1696` 中 `--auto` 强制追加 `--phase1` 的代码
→ `--from-digest` 现在可通过 `WIKI_LLM_DIRECT=1` 直接合入，或显式 `--phase1` 走 task 文件模式
→ 合入失败时打印诊断信息

### P1: arxiv2md 缓存内容错乱
→ `safe_download_arxiv()` 缓存读取时从 frontmatter/content 提取 arxiv ID 做内容指纹校验
→ 缓存 ID 与期望 ID 不匹配时自动失效并重新下载
→ `rename_file_by_title()` WinError 183 处理：rename 前先 unlink 已有文件

### P1: arxiv2md 输出缺少 `# Title` 标题行
→ 新增 `_ensure_title_header()` 工具函数
→ 如果内容缺少 `# Title`，从 YAML frontmatter `title:` 字段或首行 `##` 提取并补写
→ `safe_download_arxiv()` 的所有路径（CLI/API/webfetch）均调用此函数

### P1: 合入失败无可见性
→ `run_from_digest()` 中 `ingest()` 返回 False 时打印 `[!] 合入失败: <标题>` + 原因提示

### P2: JSON 文件中文内容在 GBK 编码下崩溃
→ `feeds.py`：`open()` 调用增加 `encoding="utf-8"`
→ `query.py`、`build_graph.py`、`refresh.py`：`read_text()`/`write_text()` 增加 `encoding="utf-8"`

### P2: 源文件无内容一致性校验
→ `safe_download_arxiv()` 下载后验证内容 arxiv ID 与期望一致
→ 不一致时打印警告

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

---

## [2026-07-31] 批量修复 r3

涉及文件：`_utils.py`、`filter.py`、`deep-read.py`

### P2: phase1 任务失败后无保留/重试
→ `_utils.py` 新增 `load_manifest()`、`list_all_tasks()`、`list_pending_tasks()`、`list_failed_tasks()`、`retry_failed_tasks()`
→ `clean_task_dirs()` 改为 opt-in：只有 `--clean` 在 sys.argv 时才执行清理，默认保留 task 文件
→ 失败后的 task 文件得以保留，可运行 `--retry-failed` 重试
→ `run_phase_auto()` 输出信息更新，提示 `--retry-failed` 和 `--clean`

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

---

## [2026-07-31] 工作流静默退出、源文件自动补全、有效性校验

### P1: `run_from_digest` 对无 `- 源文件:` 字段条目静默跳过

**触发场景**：brief 中直接写的新条目（如 RadiosityGS、Mobile-GS）没有 `- 源文件:` 字段，而 `run_from_digest` 此前 `if not source_file: continue` 直接跳过，不进入自动下载流程。

**修复**：`ingest.py` `run_from_digest` — 无 `source_file` 时从 `source_url` 推断文件名（arxiv ID 或 URL slug）；每一步都 `print()` 状态：

```python
if not source_file:
    source_url = entry.get('source_url', '')
    arxiv_id = extract_arxiv_id(source_url)
    slug = arxiv_id or re.sub(...)
    source_file = f"raw/digest/sources/.../{slug}.md"
    print(f"  [i] {title} — 无源文件字段，基于 URL 推断")
```

### P1: `ingest.py --from-digest` 静默退出

**触发场景**：多个分支（无条目、日期不匹配、无 URL、下载失败）无 `print()`，用户无法判断发生了什么。

**修复**：所有提前退出的分支加 `print()` 输出原因：

- 无条目 → `print("No entries marked for wiki ingest.")`
- 日期不匹配 → `print(f"Date mismatch: {a} != {b}")`
- 无 URL → `print(f"[!] {title} — 文件不存在且无 URL，跳过")`
- 下载失败 → `print(f"[!] arxiv 自动下载失败: {e}")`

### P2: 源文件有效性校验缺失

**触发场景**：arxiv2md 解析失败时生成 0 字节或仅 3 行的无效文件（如 GlossyGS 的 "Untitled Document"），但下游 ingest 仍尝试处理。

**修复**：`run_from_digest` 中 `safe_download_arxiv` 后校验：

```python
if out_path.exists() and out_path.stat().st_size > 100:
    entry['file_path'] = out_path  # 接受
else:
    print(f"[!] 文件过小 ({size} bytes)，跳过")
    out_path.unlink(missing_ok=True)
```

### P2: `health.py` check_overview_sync GBK 编码崩溃

**触发场景**：中文 Windows 上 `subprocess.run(capture_output=True, text=True)` 使用 GBK 解码输出，遇到非 GBK 字节时 `_readerthread` 崩溃，导致 `fix.stdout` 为 `None`。

**修复**：`tools/health.py` — 添加 `encoding='utf-8', errors='replace'` 参数：

```python
ENCODING_ARGS = dict(encoding='utf-8', errors='replace')
check = subprocess.run(..., **ENCODING_ARGS)
```

### P2: arxiv2md `-o` 嵌套目录 bug

**触发场景**：`arxiv2md -o path/file.md` 把 `path/file.md` 当目录创建，内部生成 `<Title>.md`，导致调用方混淆。

**修复**（arxiv2md 仓库）：`src/arxiv2md/__main__.py` — 判断 `-o` 后缀为 `.md` 时直接写文件，否则按原目录行为。

```python
if output_path.suffix.lower() == ".md":
    output_path.parent.mkdir(parents=True, exist_ok=True)
else:
    # 保持原目录行为
    title = _extract_title(...)
    filename = _sanitize_filename(title) + ".md"
    output_path = output_path / filename
```

### P2: `health.py` `check_overview_sync` GBK 编码崩溃

**触发场景**：中文 Windows 上 `subprocess.run(capture_output=True, text=True)` 使用系统默认 GBK 解码，遇到非 GBK 字节时 `_readerthread` 崩溃，`fix.stdout` 为 `None`，触发 `AttributeError: 'NoneType' object has no attribute 'strip'`。

**修复**：`tools/health.py` — 添加 `encoding='utf-8', errors='replace'` 参数 + None 安全取值：

```python
ENCODING_ARGS = dict(encoding='utf-8', errors='replace')
check = subprocess.run(..., **ENCODING_ARGS)
# 同时 fix.stdout → (fix.stdout or "").strip()
```
