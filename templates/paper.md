#### Paper Template (`raw/papers/`)
```markdown
---
title: "Paper Title"
type: source
tags: [paper]
date: YYYY-MM-DD
source_file: raw/papers/...
url: ""           # 原始出处 URL（arxiv、doi、项目页等）
venue: ""          # 会议或期刊名，如 CVPR 2025
published: YYYY    # 发表年份
links: []          # 代码或项目链接
---

## Summary
2–4 句概述论文解决的问题、核心方法和主要贡献。

## 原始出处
- 原始文件: [{source_file}](../../{source_file})
- 原文链接: [{url}]({url})

## Key Contributions
- Contribution 1
- Contribution 2

## Method
详细描述论文的核心方法、技术流程、算法步骤和实现细节。包括模型架构、训练策略、关键模块设计、数据流和推理过程。避免泛泛而谈，要写出可复现的技术细节。

核心架构概览，包括 pipeline 结构、输入输出、关键模块及其交互关系。可使用流程图辅助说明。

**模块/组件细节**：
- **组件 1**: 功能、设计选择和数学公式（如有）
- **组件 2**: 同上

**论文中的框架图、流程图、步骤图等必须写入**：引用时使用 `![描述](../images/<source-slug>/文件名)` 格式（注意路径相对于 `wiki/sources/`），图片放在对应标题下方并附简要文字说明。不要遗漏任何与技术流程相关的图示。

**下载外部图片**：所有图片必须保存在本地 `wiki/images/<source-slug>/` 目录下。使用 `curl` 或 `wget` 下载图片到该目录，图片文件名保持简洁（如 `pipeline.png`、`architecture.png`、`results.png`）。如果源文档中图片是 base64 嵌入，需提取并保存为独立图片文件。

## Training
- 目标函数 / Loss 设计
- 训练策略、超参数、调度器
- 数据需求与预处理

## Results & Comparisons
总结论文的实验结果，特别是与相关工作中其他方法的对比数据。包括指标对比、优劣分析。如果对比了重要工作，记录对比结果，并分析论文方法与对应相关工作的**相同点和不同点**（设计思路、假设条件、适用场景等）。

## Related Work Analysis
如果论文本身没有在 Results 中详细对比某个重要相关工作，在此处补充：列出论文与该工作的关键异同，包括技术路线、假设条件和性能差异。

## Ablations
关键消融实验及其结论，提炼每个消融揭示的设计原则。

## Limitations
论文自述的局限性，或 reviewer 指出的问题。

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

