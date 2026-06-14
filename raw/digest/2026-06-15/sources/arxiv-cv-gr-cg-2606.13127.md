---
title: "Fully Distributed Multi-View 3D Tracking in Real-Time"
arxiv_id: "2606.13127"
url: https://arxiv.org/abs/2606.13127
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Fully Distributed Multi-View 3D Tracking in Real-Time
**作者**: Byron Hernandez, Fangyu Li, Aotian Wu, Paul J. Shin, Kaustubh Purandare, Henry Medeiros
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.13127
**提交日期**: 2026-06-11

**摘要**:
Multi-camera tracking with overlapping fields of view typically relies on centralized fusion, which creates computational bottlenecks that prevent deployment at scale. We present MV3DT, a fully distributed framework for real-time multi-view 3D tracking that achieves accurate identity propagation and occlusion recovery through peer-to-peer coordination, eliminating the need for central aggregation. Each camera node executes a lightweight modular pipeline comprising monocular 3D perception, distributed multi-view association, and collaborative fusion via lightweight messaging. MV3DT achieves 94.3% IDF1 and 93.3% MOTA on WILDTRACK, competitive with state-of-the-art centralized methods, while demonstrating superior scalability by sustaining 30 FPS on 100 cameras with less than 10 ms inter-camera latency and only 2.2% communication overhead. MV3DT operates in a zero-shot regime given camera calibrations, requiring no scene-specific learning and making it directly deployable in new environments. These results establish MV3DT as a practical solution for real-time multi-view tracking in large-scale overlapping camera networks.
