---
title: "Learning Task-Aware Sampling with Shared Saliency through Density-Equalizing Mappings"
arxiv_id: "2606.12869"
url: https://arxiv.org/abs/2606.12869
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Learning Task-Aware Sampling with Shared Saliency through Density-Equalizing Mappings
**作者**: Tsz Lok Ip, Han Zhang, Lok Ming Lui
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.12869
**提交日期**: 2026-06-11

**摘要**:
In image and surface-based learning tasks, convolutional features are typically extracted using receptive fields that are sampled uniformly across the entire domain. However, informative structures are rarely distributed uniformly in practice and are often concentrated in localized regions. Such phenomena are particularly common in medical imaging, where pathological changes are spatially confined. Consequently, uniform convolution allocates equal computational effort to both informative and uninformative regions, resulting in inefficient feature extraction and suboptimal utilization of model capacity. To address this issue, we propose a framework for task-adaptive sampling that dynamically redistributes computational attention according to the spatial importance of the data. Specifically, we introduce the Density-Equalizing Convolutional Neural Network (DECNN), which employs density-equalizing mappings to guide convolution through a learned density function. The density function encodes the relative importance of different regions and induces a transformation that enlarges informative areas while compressing less relevant ones. As a result, convolutional receptive fields are redistributed non-uniformly over the domain, enabling denser sampling in task-relevant regions. By coupling this importance-driven transformation with convolution, DECNN performs adaptive feature extraction that focuses computational resources on informative structures. This leads to more efficient use of model capacity, yielding a lightweight yet expressive architecture while simultaneously producing an interpretable saliency map. Experiments on image classification and craniofacial surface analysis demonstrate that DECNN achieves competitive or superior performance with fewer parameters, accurately identifies task-relevant regions, and remains robust under complex geometric variations.
