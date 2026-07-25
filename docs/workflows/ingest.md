# Ingest Workflow

Triggered by: *"ingest <file>"*

**Supported formats:** Markdown (`.md`) is ingested directly. Non-markdown files (`.docx`, `.pptx`, `.xlsx`, `.html`, `.txt`, `.csv`, `.json`, `.xml`, `.rst`, `.rtf`, `.epub`, `.ipynb`, `.yaml`, `.yml`, `.tsv`, `.wav`, `.mp3`) are auto-converted to markdown via [markitdown](https://github.com/microsoft/markitdown) before ingestion. **arXiv 论文优先用 `arxiv2md`（解析 HTML，保留公式和结构）**，PDF 文件用 `tools/pdf2md.py`。Use `--no-convert` to skip auto-conversion.

Steps (in order):
1. **arXiv 论文** — `arxiv2md <arxiv_id> -o <output.md>`（推荐，解析 HTML 版本，保留 MathML/公式）。若失败则 fallback 到 `tools/pdf2md.py`。
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
