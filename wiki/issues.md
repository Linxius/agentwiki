# Wiki Issues

本文件记录 wiki 中已知但不阻塞当前流程的问题，供后续批量处理参考。
由 agent 手动或通过 lint/graph report 自动追加。

## Pending Entities

在多个 source 中被引用但尚未创建独立页面的 entity/concept。

_待 lint 或手动记录后填充_

## Phantom Links

`[[PageName]]` 引用了不存在的页面。由 lint 检测（引用数 ≥ 2 的标记为 Phantom Hub，确认后自动创建 stub）。

_待 lint 执行后追加_

## Orphan Pages

没有任何 inbound [[link]] 的页面。由 lint 检测。

_待 lint 执行后追加_

## Stale Pages

新 source 摄入后未同步更新的旧页面。由 lint 检测（需 LLM）。

_待 lint 执行后追加_

## Contradictions

跨页面存在矛盾声明。由 lint 检测（需 LLM）。

_待 lint 执行后追加_

## Misclassification

页面的 `type: entity|concept` 分类与内容不符。由 lint 检测（需 LLM）。

_待 lint 执行后追加_

## Fragile Bridges

知识图谱中社区之间仅 1 条边连接的脆弱结构。由 lint 检测。

_待 lint 执行后追加_

## Isolated Communities

与其他部分完全隔离的聚类。由 lint 检测。

_待 lint 执行后追加_- `wiki\sources\stub-test.md` — stub, 26 bytes

