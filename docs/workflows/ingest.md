# Ingest Workflow

Triggered by: *"ingest <file>"*

**Supported formats:** Markdown (`.md`) is ingested directly. Non-markdown files (`.docx`, `.pptx`, `.xlsx`, `.html`, `.txt`, `.csv`, `.json`, `.xml`, `.rst`, `.rtf`, `.epub`, `.ipynb`, `.yaml`, `.yml`, `.tsv`, `.wav`, `.mp3`) are auto-converted to markdown via [markitdown](https://github.com/microsoft/markitdown) before ingestion. **arXiv 论文优先用 `arxiv2md`（解析 HTML，保留公式和结构）**，PDF 文件用 `tools/pdf2md.py`。Use `--no-convert` to skip auto-conversion.

Steps (in order):
1. **arXiv 论文** — `arxiv2md <arxiv_id> -o <output.md>`（推荐，解析 HTML 版本，保留 MathML/公式）。自动经 multi-tier 回退链：arxiv2md CLI/API → alphaXiv overview → arxiv HTML5 → abstract webfetch，全部失败时标记 `agent_action: fetch_alphaxiv` 待 MCP 补全。
2. **PDF** — `tools/pdf2md.py <path>` (timeout ≥600s). Read `.md` output.
2. **Book splitting** — dir: use chapter files. Single file: split by `##` into `raw/books/<slug>/*.md`.
3. Extract original URL from frontmatter/arXiv ID/content — if none, ask user.
4. Read `wiki/index.md` + `wiki/overview.md` for context.
5. Write source page(s) using template (`templates/`). Set `source_file` + `url`, include `## 原始出处`.
6. **Download images** — `tools/download-images.py <slug>` to `wiki/images/<slug>/`.
7. Update `wiki/index.md` (Sources section) + `wiki/overview.md` (if warranted).
8. Update/create entity (companies/projects/products, **NOT** paper authors) + concept pages.
9. If paper compares with important related work, create source pages for those works.
10. Flag contradictions → `wiki/issues.md` (Contradictions).
11. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <Title>`.
12. **Post-ingest validation** — `validate-wiki.py` checks broken `[[wikilinks]]` + index coverage. Append broken links to `wiki/issues.md` (Phantom Links).
13. Run `health` as post-ingest integrity check.

### Concept Distinction

区分通用概念页（跨论文方法对比，多 sources 标签）与方法具体实现页（单 source 标签），避免混用。例：`FrameGeneration.md`（List 3DWarp/BSR/Mob-FGSR/DLSS3）vs `MobFGSR.md`（论文具体方法）。

### Source-Type Templates

All source pages use templates under `templates/`:

- [Generic Template](templates/generic.md) (fallback)
- [Paper](templates/paper.md) / [Article](templates/article.md) / [Book](templates/book.md) / [Dataset](templates/dataset.md) / [Doc](templates/doc.md) / [Project](templates/project.md) / [Talk](templates/talk.md)

Matched by: `raw/{papers,articles,books,datasets,projects,talks}/` prefix in source file path.

## Direct Ingest（跳过 inbox/filter/deep-read）

Triggered by: *"ingest paper <url>"* / *"直接合入 <url>"* / `python tools/ingest.py --paper <url-or-arxiv-id>`

跳过全部流程，直接下载并合入 wiki。

```bash
python tools/ingest.py --paper https://arxiv.org/abs/2401.12345
python tools/ingest.py --paper 2401.12345
python tools/ingest.py --paper /path/to/paper.pdf
python tools/ingest.py --paper https://example.com/article
```

**Agent 工作流：**
1. 检测输入类型 → 转换为 markdown（arxiv → `arxiv2md`，PDF → `pdf2md.py`，网页 → `webfetch` + trafilatura）
2. 运行 `python tools/ingest.py <output.md>` 合入 wiki
3. 更新 `wiki/log.md` 和 `wiki/index.md`

## Fallback: Brief 直接合入

当源文件缺失且无法自动获取时（如 GitHub 项目源文件已被删除），可用 brief 详细报告直接合入：

1. **源文件不足时**：用 brief 详细报告中的方法分析作为内容来源；用 `webfetch` 抓取网页/README 作为补充
2. **写入 raw/{type}/<slug>.md**：创建带 frontmatter 的源文件（title/url/date/source_file）
3. **创建 wiki/sources/<slug>.md**：按对应模板（paper/article/project）
4. **更新 wiki/index.md、wiki/overview.md、wiki/log.md**
5. **更新 raw/digest/brief.md** 状态为 `[x] 已合入 wiki`

`ingest.py --from-digest` 已支持非 arxiv URL 自动抓取（`_utils.fetch_web_source()`），大多数场景无需手动 fallback。

## Ingest from Digest（Stage 3）

Triggered by: *"ingest from digest"* or `python tools/ingest.py --from-digest YYYY-MM-DD`

可直接对 brief.md 中勾选了 `[x] 合入 wiki` 的条目执行，无需先深度阅读。

**Token 节省：** 如有深度阅读报告（deepdive.md），直接使用其中内容生成 wiki 页面，**不要重读原文**。仅当深度阅读缺少关键细节时才按需读对应章节。

Steps:
1. Read brief.md to find entries marked `[x] 合入 wiki`
2. Find corresponding files in `digest/YYYY-MM-DD/sources/`
3. If deep-read report exists for this entry, use it as primary content source
4. Show list to user for category confirmation
5. Move files to appropriate category directory (raw/{papers,articles,...}/)
6. Run ingest() for each file (follows standard Ingest Workflow steps)
7. Update brief.md status

### ⚠️ 评论/启示自动携带

合入 wiki 时，如果对应条目有：
- 用户在 brief 中写的备注 → 自动传递给 ingest prompt
- 深度阅读报告中的"启示/思考"部分 → 自动提取并传递给 ingest prompt
- 用户直接发给 agent 的评论 → 由 agent 记入 session 状态，在 ingest 时写入

这些内容将在 `## 评论与启示` 章节中呈现。

### 评论与启示写入原则

**原则：** 无论来自 brief 中的用户评论、深度阅读报告的启示、还是用户直接发给 agent 的评论，agent 应主动将其整合到 wiki 页面。

**写入方式：**
- 在 wiki 页面的 `## Limitations` 之后新增 `## 评论与启示` 章节
- 评论包括：个人见解、与其他工作的对比思考、未来方向建议、实践心得等
- 章节内容保留评论来源引用（如"来自 deep-read 报告"或"用户手动添加"）
- 合入 wiki 时，prompt 中携带评论内容，由 LLM 决定如何整合

**Agent 主动检测：**
- Deep-read 报告末尾如有"启示/思考"内容 → 自动带入 ingest prompt
- 用户提交评论 → 记入 session 状态，在 ingest 时写入
- Brief.md 条目中用户额外写的备注 → 随 brief 数据一并传递给 ingest

### ⚠️ 源文件链接规则

Wiki 页面的 `## 原始出处` 章节必须包含：
- 原始 md 文件路径（相对 wiki/sources/ 的路径）
- 原文 URL
- **Brief 条目引用**（如 brief.md 中对应的章节标题和日期）
- **深度阅读报告引用**（如 deepdive/日期/slug.md 对应的文件路径）

路径使用 `os.path.relpath()` 计算以确保**相对路径正确**，即使归档后地址改变也通过 repo 根目录重新计算。不要在 URL 中硬编码日期或路径。

### ⚠️ 模板遵从规则

**Ingest 必须严格遵循 `templates/` 中对应类型的模板。** 模板定义了：
- Frontmatter 字段（title, type, tags, date, source_file, url, venue, published, links）
- 正文章节顺序和内容要求
- 图片引用格式：`![描述](../images/<source-slug>/文件名)` 或直接使用 arxiv URL

**Paper 模板特殊要求：**
- Method 章节最前面放框架图/流程图/管线图（用 arxiv HTML URL 链接，如 `https://arxiv.org/html/.../figures/images/...`）
- 包含 Related Work Analysis 章节
- Method 章节双重写作：整体思路（直白解释设计动机）+ 复现细节（公式、超参数）

## LLM 调用模式

`ingest.py` 支持三种 LLM 调用模式，按场景切换：

### 模式 1：Task 文件模式（`--phase1` / `--phase2`）

1. **Phase1**：脚本构建 prompt，写入 `raw/.tmp/wiki-tasks/<task>.json`
2. **主代理处理**：主 agent 读取 prompt 文件，执行 LLM 推理，结果写入 `raw/.tmp/wiki-results/<task>.txt` + `.done` 标记
3. **Phase2**：脚本读取结果，解析 JSON，创建/更新 wiki 页面

```
ingest.py --phase1     → 写 task 文件
# agent 处理 task 文件
ingest.py --phase2     → 读取结果，创建页面
```

### 模式 2：直接 LLM 模式（`WIKI_LLM_DIRECT=1`）

单次运行生成 prompt，agent 处理后再运行一次完成合入：

```
WIKI_LLM_DIRECT=1 ingest.py --from-digest
# → 写 prompt 到 raw/.tmp/wiki-llm-prompt.md，打印指令
# → agent 处理 prompt，写结果到 raw/.tmp/wiki-llm-response.md
# → 重新运行相同命令（自动读取 response）
```

### 模式 3：内联模式（无特殊参数）

脚本直接调用 `call_llm()`。当 `WIKI_LLM_DIRECT` 和 `--phase1` 均未设置时，按以下优先级：已存在 RESPONSE_FILE → 直接返回内容；否则写 task 文件。

### 附加选项

| 参数 | 说明 |
|------|------|
| `--retry-failed` | 重试结果为空或失败的 task |
| `--clean` | 显式清除 task/result 文件（默认保留） |
| `--keep-phase2-results` | 保留处理后的中间产物 |

### 安全保证

- Phase1 返回 `False`，`run_from_digest` 不会删除 brief 条目或源文件
- 仅当 Phase2 成功写入 wiki 页面后才清理临时文件
- 异常时（JSON 解析失败、文件写入失败）抛出异常，brief 条目保留

