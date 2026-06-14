#### Book Template (`raw/books/`)

Books can be ingested in two forms:

**Form A — Single markdown file** (e.g., PDF converted to one large MD): follows the single-page template below.

**Form B — Directory with pre-split chapter files** (e.g., `raw/books/<book>/sourceFile/ch-*.md`): generates an overview page + one source page per chapter.

In both forms, the ingest workflow handles splitting (see [Ingest Workflow](#ingest-workflow)).

##### Single File Template (Form A)
```markdown
---
title: "Book Title"
type: source
tags: [book]
date: YYYY-MM-DD
source_file: raw/books/...
url: ""           # 原始出处 URL（如有）
---

## Summary
2–4 sentence summary of the book.

## 原始出处
- 原始文件: [{source_file}](../../{source_file})
- 原文链接: [{url}]({url})

## Structure
- Chapter N: [Title] — key idea
- Chapter N: [Title] — key idea

## Key Concepts
- [[ConceptName]] — how it connects

## Connections
- [[EntityName]] — how they relate

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

##### Book Directory Template (Form B)

###### Overview Page (`wiki/sources/<book-slug>/overview.md`)
```markdown
---
title: "Book Title"
type: source
tags: [book]
date: YYYY-MM-DD
source_file: raw/books/<book>/
url: ""           # 原始出处 URL（如有）
---

## Summary
2–4 sentence summary of the book.

## 原始出处
- 原始文件: [{source_file}](../../../{source_file})
- 原文链接: [{url}]({url})

## Chapters
- [[Ch01Introduction|Ch1: Introduction]]
- [[Ch02GraphicsPipeline|Ch2: Graphics Pipeline]]
- ...

## Key Concepts
- [[ConceptName]] — how it connects

## Connections
- [[EntityName]] — how they relate

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

###### Chapter Page (`wiki/sources/<book-slug>/ch-<NN>-<topic>.md`)
```markdown
---
title: "Ch<N>: Chapter Title"
type: source
tags: [book-chapter]
date: YYYY-MM-DD
source_file: raw/books/<book>/sourceFile/...
url: ""           # 原始出处 URL（如有）
book: "Book Title"
---

## Summary
2–4 sentence summary of the chapter.

## 原始出处
- 原始文件: [{source_file}](../../../{source_file})
- 原文链接: [{url}]({url})

## Key Points
- Point 1
- Point 2

## Key Concepts
- [[ConceptName]] — how it connects

## Connections
- [[ChapterX]] — how it relates to other chapters
- [[EntityName]] — how they relate
```

