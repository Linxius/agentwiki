#### Code Template (`raw/codes/`)
```markdown
---
title: "代码标题"
type: source
tags: [code]
date: YYYY-MM-DD
source_file: path/to/file.py
language: python
---

## Summary
2-4 句概述代码功能、技术栈和核心用途。

## 原始出处
- 原始文件: [{source_file}]({source_file})

## 框架概览
代码的整体架构描述，包括模块划分、设计思路、主要组件及其关系。

## 核心算法流程
核心业务逻辑或算法的详细流程描述，用文字逐步说明。

## 步骤详解
逐步拆解关键函数/模块的执行流程，每个步骤包含输入、处理、输出。

**步骤 1: 名称**
- 输入: ...
- 处理: ...
- 输出: ...

## 输入输出分析
主要函数/接口的输入参数、返回值、数据格式和边界条件。

## 流程图

### 整体架构图
```mermaid
graph TD
    A[模块A] --> B[模块B]
    B --> C[模块C]
```

### 核心算法流程图
```mermaid
flowchart LR
    Start[开始] --> Step1[步骤1] --> Step2[步骤2] --> End[结束]
```

### 调用关系图
```mermaid
graph LR
    Main[主函数] --> Func1[函数1]
    Main --> Func2[函数2]
    Func1 --> Helper[辅助函数]
```

## 依赖关系
外部依赖库、内部模块依赖及版本要求。

## 关键数据结构
核心数据类、字典、配置等结构定义。

## 设计模式
使用的设计模式、架构风格及其选择原因。

## Connections
- [[EntityName]] — 关联说明
- [[ConceptName]] — 概念连接

**填写要求：**
- 列出与其他 wiki 页面的关联（使用 [[PageName]] 链接）
- 说明关联的性质（如"也是超分辨率算法"、"使用类似技术"）
- 至少列出 2-3 个关联

## Contradictions
- 与 [[OtherPage]] 的矛盾点

**填写要求：**
- 列出与自身描述或其他页面的矛盾/限制
- 说明矛盾的性质（如"不支持时间性融合"、"专为特定硬件优化"）
- 至少列出 2-3 个矛盾/限制
```
