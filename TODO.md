# Wiki Pipeline 待优化清单

> 已完成项已归档至 [TODO-archive.md](TODO-archive.md)。
> 优先级：P0（数据安全/阻塞）> P1（流程缺陷）> P2（效率/质量）

---

## 待处理

### P1: `ingest.py --from-digest` 对非 arxiv 源静默跳过

**已修复**：
- [x] `_utils.py` 新增 `fetch_web_source(url, out_path)`
- [x] `run_from_digest` 扩展自动下载段：非 arxiv URL 走 `fetch_web_source`
- [x] `docs/workflows/ingest.md` 补充 Fallback 节

### P1: Phase1→Phase2 失败时静默吞错误

**已修复**：
- [x] `ingest()` 返回 `bool`：phase1 → `False`（未提交），写入 wiki → `True`
- [x] `run_from_digest` 只有 `ok == True` 时才删 brief 条目和源文件
- [x] `call_llm()` 返回空时不继续解析 JSON
- [x] `docs/workflows/ingest.md` 补充 `## Phase1/Phase2 两阶段协议` 节

### P2: 缺少"brief 直接合入"标准化路径

**已修复**：
- [x] `docs/workflows/ingest.md` 增加 `## Fallback: Brief 直接合入` 节
- [x] `_utils.fetch_web_source()` 覆盖大多数非 arxiv 自动获取场景

### P2: 合入后缺少验证步骤

**已修复**：
- [x] 由 T1.2 覆盖：`ingest()` 返回成功后才清理，写入失败时异常回滚

### P2: 源文件全流程生命周期管理

**已检查**：
- [x] 命名规则：arxiv 用 `arxiv-{id}-{slug}.md`，非 arxiv 用 `{slug}.md`，一致性足够
- [x] `raw/digest/sources/` vs `raw/papers/`：`run_from_digest` 在 `ok==True` 后已 `unlink()` 清理 digest 源文件
- [x] symlink 当前阶段不需要——digest 源在 ingest 后即清理，不保留残留

---

## 后续触发词速查

| 你想... | 说 |
|--------|-----|
| 加载项目优化 skill | `load wiki optimize skill` |
| 外部化 AGENTS.md 更多内容 | `externalize agents content` |
| 查看已完成优化 | `read TODO-archive.md` |
