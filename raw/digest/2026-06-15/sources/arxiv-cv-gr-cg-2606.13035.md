---
title: "TetherCache: Stabilizing Autoregressive Long-Form Video Generation with Gated Recall and Trusted Alignment"
arxiv_id: "2606.13035"
url: https://arxiv.org/abs/2606.13035
categories: [cs.CV,cs.AI]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: TetherCache: Stabilizing Autoregressive Long-Form Video Generation with Gated Recall and Trusted Alignment
**作者**: Yu Meng, Xiangyang Luo, Letian Li, Wenyuan Jiang, Chen Gao, Xinlei Chen, Yong Li, Xiao-Ping Zhang
**分类**: cs.CV, cs.AI
**arXiv**: https://arxiv.org/abs/2606.13035
**提交日期**: 2026-06-11

**摘要**:
Autoregressive video diffusion models provide a natural formulation for streaming and variable-length video generation by conditioning newly generated frames on previously generated content. However, extending these models to minute-level generation remains challenging: the limited KV-cache budget prevents the model from retaining the full history, while repeatedly conditioning on self-generated frames induces a context distribution shift that accumulates over time, leading to visual artifacts, quality degradation, and temporal drift. In this paper, we propose TetherCache, a training-free and plug-and-play cache management strategy for drift-resistant long video generation. TetherCache organizes the cache into sink, memory, and recent regions, and introduces two complementary mechanisms. First, GRAB (Gated Recall with Attention-Diversity Balancing) selects long-range memory frames using a gated score that combines attention-based relevance with temporal diversity, preserving informative yet diverse historical context under a fixed cache budget. Second, TAME (Trusted Alignment via Memory Editing) lightly edits newly recalled memory tokens by aligning their statistics to a trusted context distribution, reducing the pollution caused by drifted historical features. Built on Self-Forcing, TetherCache consistently improves long-video generation quality on VBench-Long across 30s, 60s, and 240s settings. In particular, for 240s generation, it substantially improves overall and semantic scores while reducing quality drift from 7.84 to 1.33, demonstrating its effectiveness for stable long-horizon autoregressive video diffusion.
