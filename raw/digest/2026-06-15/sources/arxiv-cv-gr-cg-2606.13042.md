---
title: "Augmentation techniques for video surveillance in the visible and thermal spectral range"
arxiv_id: "2606.13042"
url: https://arxiv.org/abs/2606.13042
categories: [cs.AI,cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Augmentation techniques for video surveillance in the visible and thermal spectral range
**作者**: Vanessa Buhrmester, Ann-Kristin Grosselfinger, David Munch, Michael Arens
**分类**: cs.AI, cs.CV
**arXiv**: https://arxiv.org/abs/2606.13042
**提交日期**: 2026-06-11

**摘要**:
In intelligent video surveillance, cameras record image sequences during day and night. Commonly, this demands different sensors. To achieve a better performance it is not unusual to combine them. We focus on the case that a long-wave infrared camera records continuously and in addition to this, another camera records in the visible spectral range during daytime and an intelligent algorithm supervises the picked up imagery. More accurate, our task is multispectral CNN-based object detection. At first glance, images originating from the visible spectral range differ between thermal infrared ones in the presence of color and distinct texture information on the one hand and in not containing information about thermal radiation that emits from objects on the other hand. Although color can provide valuable information for classification tasks, effects such as varying illumination and specialties of different sensors still represent significant problems. Anyway, obtaining sufficient and practical thermal infrared datasets for training a deep neural network poses still a challenge. That is the reason why training with the help of data from the visible spectral range could be advantageous, particularly if the data, which has to be evaluated contains both visible and infrared data. However, there is no clear evidence of how strongly variations in thermal radiation, shape, or color information influence classification accuracy. To gain deeper insight into how Convolutional Neural Networks make decisions and what they learn from different sensor input data, we investigate the suitability and robustness of different augmentation techniques...
