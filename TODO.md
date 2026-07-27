# Wiki Pipeline 待优化清单

> 优先级：P0（阻塞/数据安全）> P1（流程缺陷）> P2（效率/质量）
> 
> 更新：2026-07-28 — 新增 deep-read/子代理 session 发现的问题

---

## P0 — 阻塞性问题

### [ ] `call_llm()` 已作废但仍有直接调用点
- **问题**：`_utils.py:42` `call_llm()` 现已 `print + sys.exit(1)`，但以下函数仍直接调它（不带 `--phase1/--phase2` 时必崩溃）：
  - `ingest.py:272` `update_interests_from_ingest`
  - `ingest.py:753` `ingest()` 默认模式
  - `deep-read.py:494, 563, 622` 正常模式（已 deprecated）
  - `filter.py:278`, `lint.py:284`, `query.py:186/232/254`, `heal.py:121`
- **影响**：这些工具的"普通模式"全部不可用，必须全部迁移到 phase1/phase2 或直接移除
- **修复**：逐一迁移或删代码

### [ ] `RESULT_DIR` 从未被创建
- **问题**：`prepare_tasks` 创建 `TASK_DIR`（`raw/.tmp/wiki-tasks/`），但没有任何代码创建 `RESULT_DIR`（`raw/.tmp/wiki-results/`）。子代理需自行 mkdir，如果失败则结果丢失
- **影响**：`read_results()` 静默返回 `{}`，phase2 行为不一致：
  - `ingest.py` → `sys.exit(1)`（硬失败）
  - `deep-read.py` → 写 `⚠️ 无结果`（软失败）
  - `filter.py` → 追加到 `failed_files`（最佳方式）
- **修复**：`prepare_tasks()` 或 `prepare_task()` 中创建 `RESULT_DIR`

### [ ] 子代理无写入同步机制
- **问题**：`deep-read.py` 的 phase2 读取 `RESULT_DIR/*.txt`，但子代理可能尚未写完。无锁/无就绪标记
- **影响**：竞态条件下 phase2 读到空/不完整结果，静默产生 `⚠️ 无结果`
- **修复**：子代理写入完成后写一个 `.done` 标记，phase2 等待所有 `.done` 就绪

---

## P1 — 流程缺陷

### [ ] deep-read.py phase1 同时处理不感兴趣 + 深度阅读
- **问题**：`run_deep_read()` 的 phase1 分支先处理不感兴趣条目，写入 task 后 `return`。深度阅读的 task **永远不会写入**。用户需 `--phase2` → 再 `--phase1` → 再 `--phase2`
- **修复**：phase1 应同时写入不感兴趣和深度阅读的 task，或分两个独立函数

### [ ] filter.py `archive_current_brief()` 用 `date.today()` 而非 brief 日期
- **问题**：`filter.py:640` 归档时 `today = date.today().isoformat()`，与 brief 头部日期可能不一致
- **对比**：`deep-read.py` 已修复为从 brief header 提取日期
- **修复**：统一使用 brief 头部日期

### [ ] 源文件 / 输出文件用 arxiv ID 而非论文名
- **问题**：`sources/` 中的文件名为 `arxiv-260613345-5b8f3898.md`，`deepdive/` 中 `.tmp/` 临时文件名为 `arxiv-2509.22276.md`，无法直观识别
- **影响**：调试时需打开文件才知道内容，影响效率
- **修复**：转换阶段（`arxiv2md`、`pdf2md`、web fetch）应产出以论文标题 slug 为名的文件

### [ ] 深度阅读报告章节标题残留 prompt 指令
- **问题**：生成的报告中章节标题包含 prompt 指令文本，如 `## 论文概览（仅背景、贡献和指标，不要涉及方法细节）`、`## 技术拆解（全部方法内容，这是报告主体）`
- **影响**：用户可见的 markdown 中包含不应出现的 LLM 指令
- **修复**：prompt 中不要用括号注明要求，或用 post-processing 清洗

### [ ] 共享上下文缓存无失效机制
- **问题**：`ingest.py` `get_shared_ingest_context()` 写 `raw/.tmp/wiki-ingest-context.md` 后模块级缓存 `_SHARED_CONTEXT_PATH` 永不失效。phase1 到 phase2 之间如果 wiki 变更，phase2 仍用旧缓存
- **影响**：连续两次 ingest 间，第二次的子代理读到过时的 wiki state
- **修复**：加时间戳或版本号，每次 `prepare_tasks()` 时重新生成

### [ ] deep-read.py `--file` 模式不走 phase1/phase2
- **问题**：`--file` 模式（第 697-734 行）直接搜索 brief 标题并调用 `call_llm` 生成报告，但 `call_llm` 已废弃，此路径必崩溃
- **修复**：`--file` 模式也应迁移到 phase1/phase2 或移除

---

## P2 — 效率/质量改进

### [ ] 子代理 prompt 过大导致超时/失败
- **问题**：单个子代理处理多篇论文时，prompt 含全部论文内容（每篇 ~20KB），导致上下文超限或超时
- **触发场景**：`batch subagent` 或一次性 spawn 5 篇 deep-read
- **方案**：固定每子代理 1 篇论文，或共享 schema 后每篇增量 prompt <5KB

### [ ] 子代理自恢复行为不一致
- **问题**：task 文件缺失时，部分子代理（Compact Latents, TopoMesh, World Tracing）通过 alphaXiv 自恢复获取内容，部分（GS-2M, Surflo）直接失败
- **影响**：不可预测的行为——依赖子代理的"主动性"而非协议保证
- **修复**：phase1 保证 task 文件存在，子代理不自行 fallback（统一在 phase1 预处理）

### [ ] 子代理输出格式不统一
- **问题**：部分子代理用 ` ```markdown ``` ` 包裹输出，部分纯文本。phase2 的 `re.sub(r"^```(?:markdown)?\s*", ...)` 尝试清洗但不保证全覆盖
- **修复**：子代理 prompt 中明确"纯文本，无代码块包裹"，或 phase2 做 robust strip

### [ ] 深度阅读图片引用分散
- **问题**：部分子代理引用本地 `images/xxx.png`，部分引用 arxiv HTML 直链（如 `![](https://arxiv.org/html/.../x2.png)`）。本地图片需 phase1 提前下载
- **影响**：arxiv 直链在离线或无网络环境无法显示
- **优化**：phase1 统一下载全部图片到 `images/` 并替换引用为本地路径

### [ ] `deepdive.md` 索引进度文件可能被意外删除
- **问题**：phase2 输出的 `deepdive/日期/deepdive.md` 索引文件在某些情况消失（疑似 cleanup 误伤或文件系统延迟），原因未明
- **影响**：phase1 dedup 依赖此文件检查已处理的条目，缺失会导致重复生成
- **临时方案**：phase1 检查时如索引不存在但单独文件存在，也视为已处理

### [ ] filter 的不感兴趣 / 排除列表分析不完善
- **问题**：`filter.py` 在生成 brief 时建议新增兴趣/排除项，但建议仅输出到控制台，未被自动合入 `interests.md`
- **改进**：增加 `--apply-suggestions` 参数自动合入，或生成可编辑的 diff 文件

---

## Done ✓

### P0 修复
- [x] **TASK/RESULT_DIR 从 `/tmp/` 移到 `raw/.tmp/`** → `_utils.py`，消除子代理写入授权阻塞
- [x] **`run_from_digest` move→copy2 源文件生命周期** → `ingest.py`，失败后保留 sources/ 副本
- [x] **`input()` 全面 `isatty` 保护** → `ingest.py`，合并组分类 + 确认对话框双重保护

### P1 修复
- [x] **`build_brief_from_json` 日期统一** → `filter.py`，从源文件实际目录提取日期
- [x] **`fetch-sources.py` 解析只处理 `####` 条目** → 跳过 `###` 分组头
- [x] **`fetch-sources.py` 支持 `--all` 批量** → 无日期限制时处理全部
- [x] **deep-read.py 归档/清空破坏勾选状态** → 改用 MD5 内容哈希去重，不再清空 brief.md
- [x] **deep-read.py 归档日期用 brief header 日期** → 替代 `date.today()`
- [x] **deep-read.py 图片 cleanup 误删 deepdive.md** → 图片放 `images/` 子目录，不与报告同级
- [x] **deep-read.py TASK_DIR 未导入** → 补 `from _utils import TASK_DIR`
- [x] **deep-read.py phase1 dedup 不检查 `⚠️ 无结果`** → 有效报告才跳过

### P2 修复
- [x] **共享上下文文件缓存** → `ingest.py` `get_shared_ingest_context()`，~68KB schema 由子代理 `read` 而非内联（省 ~68KB/task）
- [x] **深度阅读源文件定位** → `deep-read.py` `_find_source_file()`，搜索 `raw/papers|articles|...` 分类目录，减少重抓取
- [x] **深度阅读输出路径** → `deepdive/日期/{slug}.md` 独立文件 + `deepdive.md` 索引
- [x] **深度阅读图片引用路径** → `images/{filename}` 而非 `deepdive/{filename}`
- [x] **概览/技术拆解重叠** → prompt 重写：概览仅 4 句不含方法细节，技术拆解为报告主体
- [x] **日期过滤从 per-entry 改为 brief 头部检测** → `ingest.py` `run_from_digest()`
- [x] **源文件路径跨日期目录搜索** → `ingest.py` `run_from_digest()`
- [x] **`source.relative_to()` 前 `.resolve()` 统一绝对路径** → `ingest.py` `ingest()`
- [x] **`clean_task_dirs()` 移出 `ingest()` 到全部 phase2 后** → `ingest.py`
- [x] **`--from-digest` 默认分类用 `papers` 而非 domain** → `ingest.py`
- [x] **图片选择 prompt 重写为 P0/P1/P2 优先级 + 位置约束** → `ingest.py`
- [x] **图片优先使用 arxiv URL 而非本地下载** → `ingest.py`

---

## 后续触发词速查

| 你想... | 说 |
|--------|-----|
| 检查所有 `call_llm` 调用点 | `check call_llm` |
| 修复 RESULT_DIR 创建 | `fix result dir` |
| 拆分 deep-read phase1 两阶段 | `fix deep-read phase1` |
| 统一 filter.py 归档日期 | `fix filter archive date` |
| 检查子代理同步机制 | `fix subagent sync` |
| 重命名源文件为论文名 | `rename sources` |
