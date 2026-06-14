---
title: "Camera and LiDAR BEV Fusion for Cooperative 3D Object Detection on TUMTraf V2X"
arxiv_id: "2606.12981"
url: https://arxiv.org/abs/2606.12981
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Camera and LiDAR BEV Fusion for Cooperative 3D Object Detection on TUMTraf V2X
**作者**: Muhammad Shahbaz, Shaurya Agarwal
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.12981
**提交日期**: 2026-06-11

**摘要**:
We describe a Camera and LiDAR fusion detector developed for the TUMTraf V2X cooperative 3D object detection track of the DriveX 2026 challenge. The detector fuses three roadside cameras with a fused infrastructure-plus-vehicle point cloud in a shared bird's-eye-view space and predicts boxes through a CenterPoint-style head with a generalized IoU regression loss and an IoU quality re-ranking head. Trained on the provided train and validation splits, the model reaches a 3D mAP of 0.85 on the public Codabench test split. While iterating on the system, we observed that 44 of the 50 test frames are also present in the released train (40) and validation (4) splits with their labels. We therefore conducted two additional studies to quantify how this overlap affects the final score: (1) a finetuning run that oversamples the 44 overlapping frames, reaching 0.89 mAP, and (2) a post-processing run that replaces predictions on those frames with the released ground truth, reaching 0.99 mAP (uploaded to our Codabench account for testing but not published on the leaderboard). All three configurations and their per-class results are reported.
