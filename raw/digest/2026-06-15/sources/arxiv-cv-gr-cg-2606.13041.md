---
title: "SeamEdit: A Black-Box VLM-Agnostic Pipeline for Large-Image Semantic Editing"
arxiv_id: "2606.13041"
url: https://arxiv.org/abs/2606.13041
categories: [cs.CV,cs.GR,cs.MM]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: SeamEdit: A Black-Box VLM-Agnostic Pipeline for Large-Image Semantic Editing
**作者**: Xiangyu Lyu, Dan Lei
**分类**: cs.CV, cs.GR, cs.MM
**arXiv**: https://arxiv.org/abs/2606.13041
**提交日期**: 2026-06-11

**摘要**:
Semantic region editing for large images must satisfy two requirements at the same time: high generative quality and natural integration with surrounding content. Some related methods rely on white-box models and leave the strong generation capability of closed-source models underexplored. Directly applying closed-source models to tiled editing, however, introduces several failure modes: semantic deformation, canvas-level alignment drift, and visible seam artifacts. This paper presents SeamEdit, a training-free and model-agnostic pipeline that treats any VLM with inpainting capability as a black-box oracle. SeamEdit mitigates these issues through a five-stage post-hoc pipeline: overlay-based tile decomposition, black-box VLM inpainting, geometric and color-consistency correction, seam-risk-based multi-candidate ranking, and dynamic-programming curved seam fusion. The pipeline reduces seam visibility and supports semantic modification of arbitrary tile regions.
