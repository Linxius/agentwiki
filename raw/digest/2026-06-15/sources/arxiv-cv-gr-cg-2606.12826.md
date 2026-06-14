---
title: "DIMOS: Disentangling Instance-level Moving Object Segmentation"
arxiv_id: "2606.12826"
url: https://arxiv.org/abs/2606.12826
categories: [cs.CV,cs.AI]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: DIMOS: Disentangling Instance-level Moving Object Segmentation
**作者**: Hongxiang Huang, Hongwei Ren, Xiaopeng Lin, Yulong Huang, Zeke Xie, Bojun Cheng
**分类**: cs.CV, cs.AI
**arXiv**: https://arxiv.org/abs/2606.12826
**提交日期**: 2026-06-11

**摘要**:
Moving instance segmentation (MIS) attracts increasing attention due to its broad applications in traffic surveillance, autonomous driving, and animal tracking. Event cameras record asynchronous brightness changes, providing high temporal resolution and dynamic range, which makes them highly sensitive to motion information. By fusing event and image features, motion cues from events can complement spatial details from images, enhancing the performance of MIS. However, current multimodal MIS methods still struggle to segment small moving instances, as event cameras often yield sparse features under limited resolution. Moreover, event features entangle appearance attributes with motion cues, which further restricts effective cross-modal fusion. To address these challenges, we first propose a dual-disentangling feature extraction framework that separates and extracts appearance and motion information within both image and event modalities, thereby improving feature density. Subsequently, a multi-granularity cross-modal alignment is introduced to align distributionally and semantically consistent features across modalities, enabling more effective fusion with rich spatial and temporal details. The experiment results demonstrate that our method achieves state-of-the-art performance in multimodal MIS, especially for small instances under challenging conditions such as fast motion and low-light settings.
