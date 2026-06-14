---
title: "YOLO-AMC: An Improved YOLO Architecture with Attention Mechanisms for Building Crack Detection"
arxiv_id: "2606.12958"
url: https://arxiv.org/abs/2606.12958
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: YOLO-AMC: An Improved YOLO Architecture with Attention Mechanisms for Building Crack Detection
**作者**: Ching-Yu Tsai, Chia-Min Lin, Chih-Hsiang Yang, Yung-Che Wang, Jen-Shiun Chiang
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.12958
**提交日期**: 2026-06-11

**摘要**:
Crack detection plays an important role in infrastructure inspection and Structural Health Monitoring (SHM). However, cracks typically appear as thin, low-contrast structures and are easily affected by background noise, posing challenges for existing object detection models. This study proposes an improved YOLO-based architecture with integrated attention mechanisms, termed YOLO-AMC (YOLO with Attention Mechanisms for Crack Detection), to enhance automated crack detection performance. Based on YOLOv11, the original C2PSA module is removed, and multiple attention mechanisms, including Global Attention Mechanism (GAM), Residual Convolutional Block Attention Module (Res-CBAM), and Shuffle Attention (SA), are introduced into the multi-scale feature fusion layers of the Neck to strengthen cross-scale feature integration. Experimental results demonstrate that YOLO-AMC consistently outperforms baseline models YOLOv11n and YOLOv8n across multiple evaluation metrics. Among the evaluated attention modules, GAM achieves the best detection performance, obtaining mAP@0.5 = 0.9917 and mAP@0.5:0.95 = 0.9506 on the test dataset, which are higher than those of YOLOv11 (0.9833 / 0.9112) and YOLOv8 (0.9707 / 0.8921). Furthermore, while maintaining a computational complexity of 7.6 GFLOPs, the proposed model achieves 110.95 FPS on an NVIDIA RTX 4090 platform and approximately 5 FPS on a Raspberry Pi 5 edge device, demonstrating a favorable trade-off between accuracy and deployment efficiency. The implementation code for this study is available on GitHub at https://github.com/CY-Tsai24/YOLO-AMC.
