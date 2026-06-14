---
title: "SAM-Deep-EIoU: Selective Mask Propagation for Multi-Object Tracking"
arxiv_id: "2606.13033"
url: https://arxiv.org/abs/2606.13033
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: SAM-Deep-EIoU: Selective Mask Propagation for Multi-Object Tracking
**作者**: Alexander Holmberg
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.13033
**提交日期**: 2026-06-11

**摘要**:
Multi-object tracking has a heavy-tailed difficulty distribution: most frames are easy for a lightweight base tracker, while a small fraction are intrinsically hard. Video object segmentation (VOS) models can often preserve identity through the hard frames where the base tracker fails, but they are much more expensive in compute and memory. We propose selective mask propagation, a tracking algorithm that dispatches from a base tracker to a VOS model only on windows where an assignment-uncertainty signal fires. The base tracker's output is modified only when the VOS model makes a confident prediction that contradicts the base tracker's identity assignment; weak or inconclusive predictions preserve the base output. The method is training-free, treats both the base tracker and the VOS model as black boxes, and can benefit from replacing the VOS component with a more capable model. On DanceTrack, selective mask propagation improves three different base trackers. On SportsMOT, where identity preservation is central to sports analytics, SAM3-Deep-EIoU with global track association achieves state-of-the-art performance on the benchmark with 86.8 HOTA.
