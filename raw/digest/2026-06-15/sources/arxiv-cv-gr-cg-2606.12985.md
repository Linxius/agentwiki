---
title: "Objects Before Words: Object-First Inductive Biases for Grounding Language in Child-View Video"
arxiv_id: "2606.12985"
url: https://arxiv.org/abs/2606.12985
categories: [cs.CV]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: Objects Before Words: Object-First Inductive Biases for Grounding Language in Child-View Video
**作者**: Sathira Silva, Abrham Kahsay Gebreselasie, Muhammad Umer Sheikh, Kartik Kuckreja, Daniel Harari, Muhammad Haris Khan
**分类**: cs.CV
**arXiv**: https://arxiv.org/abs/2606.12985
**提交日期**: 2026-06-11

**摘要**:
Learning grounded word meaning from natural experience requires resolving two ambiguities in infant-view recordings: when the named referent appears and where it is in a cluttered frame. In SAYCam-style data, caregiver speech is sparse and weakly synchronized with egocentric video, so single-frame contrastive pairing yields noisy positives in which the intended object is absent or entangled with distractors. We propose BabyMind, an object-first bias for child-view contrastive learning under sparse, noisy supervision. BabyMind extracts candidate object embeddings using an offline mask-based region interface, links candidates across a short utterance-centered window into lightweight object files via tracking, and aligns utterances to bags of object files with a prototype-space multiple-instance contrastive objective. Track-coherence and global-object agreement regularizers stabilize learning and transfer object-file structure into the global frame embedding used at evaluation. On SAYCam-S, BabyMind improves Labeled-S 15 forced-choice accuracy by +2.6 points over CVCL and yields consistent gains on in-vocabulary out-of-distribution benchmarks. Code is available at https://github.com/sathiiii/BabyMind.
