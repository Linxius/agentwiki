# Deep Read Workflow

> 从 AGENTS.md 外部化以节省常驻 token。执行深度阅读操作时阅读此文。

## Stage 2: Deep Read

Triggered by: *"generate deep-read"* or `python tools/deep-read.py --date YYYY-MM-DD`

Steps:
1. Read brief.md to find entries marked `[x] 深度阅读` and `[x] 不感兴趣`
2. For each `[x] 不感兴趣` entry, call LLM to generate interests.md update suggestions:
   - Suggest adding to 排除列表 or modifying existing interests
   - Save suggestions to `raw/digest/YYYY-MM-DD/disinterest-suggestions.md`
   - 控制台输出建议供参考
3. For each `[x] 深度阅读` entry, call LLM to generate 1500-3000 word deep-dive report:
   - Core viewpoints deep analysis
   - Technical/methodology breakdown
   - Key data/insights interpretation
   - Comparison with related fields
   - Potential issues/limitations
   - **元数据区块**：论文标题、作者、arXiv 链接、项目主页、代码仓库、对应的 brief 条目引用
   - **方法双重写作**：先写整体思路（直白解释设计动机），再写分步拆解（步骤 1/2/3 的输入→处理→输出+效果）
   - **启示/思考**：论文的启发、与已有知识的关联、未来方向建议
4. Save deep-dive reports to `raw/digest/YYYY-MM-DD/deepdive.md`

> **注意：** Stage 2 和 Stage 3 可独立触发。brief.md 中 `[x] 合入 wiki` 不需要先 `[x] 深度阅读`，可直接进入 Stage 3。

## Stage 2b: Direct Read

Triggered by: *"read paper <url>"* or *"阅读论文 <url>"* or `python tools/deep-read.py --paper <url>`

跳过 inbox 流程，直接对单篇论文/网页生成深度阅读报告。

Steps:
1. 检测输入类型：
   - arxiv URL → 提取 arxiv_id，用 `arxiv2md <arxiv_id> -o output.md` 转换（解析 HTML，保留公式/结构，图片以 URL 内嵌）
   - PDF 路径 → 用 `python tools/pdf2md.py <path>` 转换为 markdown
   - 网页 URL → 用 `webfetch` 抓取 HTML，再用 trafilatura 提取正文
2. 提取标题（从 markdown 首个 `#` 行）
3. 调用 LLM 生成深度阅读报告（与 Stage 2 相同 prompt）
4. 追加到 `raw/digest/YYYY-MM-DD/deepdive.md`

用法：
```bash
python tools/deep-read.py --paper https://arxiv.org/abs/2401.12345
python tools/deep-read.py --paper /path/to/paper.pdf
python tools/deep-read.py --paper https://example.com/article
```
