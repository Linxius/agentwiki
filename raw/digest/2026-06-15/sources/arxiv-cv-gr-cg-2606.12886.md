---
title: "Bridging Modal Isolation in Interleaved Thinking: Supervising Modality Transitions via Stepwise Reinforcement"
arxiv_id: "2606.12886"
url: https://arxiv.org/abs/2606.12886
categories: [cs.CV,cs.AI]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Bridging Modal Isolation in Interleaved Thinking: Supervising Modality Transitions via Stepwise Reinforcement
**作者**: Tingyu Li, Le Zhou, Siyuan Li, Yujun Wu, Xinglong Xu, Jingxuan Wei, Conghui He, Cheng Tan
**分类**: cs.CV, cs.AI
**arXiv**: https://arxiv.org/abs/2606.12886
**提交日期**: 2026-06-11

**摘要**:
Interleaved thinking, where a unified multimodal model alternates between textual reasoning and visual generation, has shown promise on spatial and physical tasks. However, in complex long-chain scenarios, we identify a fundamental failure mode: generated images diverge from the textual context while subsequent text ignores the visual evidence, causing the two modalities to alternate without genuinely informing each other. We term this Modal Isolation and attribute it to compounding information loss at modality boundaries. We decompose each reasoning cycle into atomic operations and define modality transition loss, quantifying cross-modal hallucination (text-to-image) and visual utilization deficit (image-to-text) at each boundary. We propose MoTiF (Modality Tiransition Fidelity), a two-stage training framework that directly optimizes these transitions: Reflective SFT trains the model to detect and recover from erroneous visual outputs; Flow-GRPO improves image generation fidelity via reinforcement learning. All training signals in MoTiF derive from transition-level fidelity rather than end-task accuracy. Across four visual puzzle benchmarks, this transition-level supervision substantially improves both cross-modal coherence and final task accuracy. The results demonstrate that effective interleaved reasoning requires explicit structural supervision at modality boundaries, not merely scaling or end-task optimization.
