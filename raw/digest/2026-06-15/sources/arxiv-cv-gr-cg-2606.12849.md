---
title: "SemanticXR: Low Power and Real-time Queryable Semantic Mapping with an Object-Level Device-Cloud Architecture"
arxiv_id: "2606.12849"
url: https://arxiv.org/abs/2606.12849
categories: [cs.DC,cs.CV,cs.RO]
source_feed: "arxiv-cv-gr-cg"
---
**标题**: SemanticXR: Low Power and Real-time Queryable Semantic Mapping with an Object-Level Device-Cloud Architecture
**作者**: Rahul Singh, Devdeep Ray, Connor Smith, Sarita Adve
**分类**: cs.DC, cs.CV, cs.RO
**arXiv**: https://arxiv.org/abs/2606.12849
**提交日期**: 2026-06-11

**摘要**:
Semantic mapping is a core service that enables grounded interactions in emerging Extended Reality (XR) applications such as AI assistants and spatial object search. Deploying this capability on mobile XR devices requires a system that is open-vocabulary, real-time, and low-power. Existing approaches are compute-intensive and assume server-class resources. Cloud offloading offers a practical path, but no existing system splits semantic mapping across the device-cloud boundary or manages its communication, execution, and memory footprint.  We present SemanticXR, the first device-cloud system for real-time, open-vocabulary semantic mapping and querying under XR power, bandwidth, and memory constraints. Our key insight is to elevate semantically identifiable objects to first-class units of communication, execution, and memory across the device and server. On the server, object-level parallelism and geometry downsampling improve mapping latency, while object-level depth-mapping co-design reduces upstream bandwidth. On the device, an object-level sparse local map with incremental updates and update prioritization enables network-robust querying with bounded memory and downstream bandwidth. Object-level configurable resource usage vs. quality trade-offs let applications and the system adapt mapping to application requirements and operating conditions, respectively.  Against a device-cloud baseline with the same perception models, object-level organization improves server-side mapping latency by 2.2X at equal semantic quality. Depth-mapping co-design maintains upstream bandwidth under 2.5 Mbps. On the device, SemanticXR sustains sub-100 ms query latency for up to 10,000 objects even under network drops, supports tens of thousands of objects within 500 MB, and scales downstream bandwidth with map changes, not total scene size. The system adds only 2% device power during normal operation.
