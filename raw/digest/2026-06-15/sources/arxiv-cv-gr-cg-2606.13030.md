---
title: "A Multi-Modal Framework with Cross-Subject Pseudo-Labeling and Semantic Alignment for Micro-Gesture Recognition"
arxiv_id: "2606.13030"
url: https://arxiv.org/abs/2606.13030
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: A Multi-Modal Framework with Cross-Subject Pseudo-Labeling and Semantic Alignment for Micro-Gesture Recognition
**作者**: Haoran Zhang, Haokun Zhang, Pengyu Liu, Yujia Zhang, Weibao Xue, Yanbin Hao
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.13030
**提交日期**: 2026-06-11

**摘要**:
Micro-gestures (MGs) are spontaneous and subtle body movements that frequently convey hidden human emotions. Recognizing MGs in untrimmed videos remains highly challenging due to their extremely low signal-to-noise ratio, severe long-tailed class distribution, and the inherent domain shift encountered in cross-subject evaluation scenarios. In this paper, we propose a comprehensive multi-modal framework for Track 1 of the 4th MiGA-IJCAI Challenge. To capture fine-grained representations, we design a saliency-guided multi-modal extraction pipeline integrating 68-keypoint skeleton joint coordinates, 3D heatmap volumes, and high-resolution RGB visual features. We introduce a gentle square-root smoothed weighting mechanism paired with an Orthogonal Semantic Embedding Loss to protect tail classes without compromising overall recognition capabilities. More importantly, to bridge the cross-subject generalization gap, we propose a Cross-Modal Pseudo-Labeling (CMPL) strategy for unsupervised domain adaptation, which significantly boosts single-modal robustness. A temperature-scaled soft-voting mechanism is finally utilized to alleviate overconfidence during late fusion. Extensive experiments demonstrate that our framework achieves a competitive F1-score of 68.13\%, securing the 4th place.
