# 环境配置与 MCP 设置

## 快速开始

```bash
git clone https://github.com/SamurAIGPT/llm-wiki-agent.git
cd llm-wiki-agent
```

打开 agent 即可使用（Claude Code / OpenCode / MiMoCode / Codex 等）：

```bash
claude      # 读 CLAUDE.md
opencode    # 读 AGENTS.md
mimocode    # 读 AGENTS.md
codex       # 读 AGENTS.md
```

## alphaXiv MCP 配置

alphaXiv 提供论文搜索、阅读、代码库访问和文献库管理的 MCP 服务。本项目将其作为 inbox 流程的补充——可以直接搜索论文并添加到 inbox，无需手动找 arXiv 链接。

### 1. 获取 API Key

访问 [alphaXiv Settings > API Keys](https://www.alphaxiv.org/settings) 创建 API key。

### 2. 配置 MCP Server

alphaXiv 使用 Streamable HTTP 传输，endpoint 为 `https://api.alphaxiv.org/mcp/v1`。

**MiMoCode** — 全局配置 `~/.config/mimocode/mimocode.json`：

```jsonc
{
  "$schema": "https://mimo.xiaomi.com/mimocode/config.json",
  "mcp": {
    "alphaxiv": {
      "type": "remote",
      "url": "https://api.alphaxiv.org/mcp/v1",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}
```

**OpenCode** — 全局配置 `~/.config/opencode/opencode.json`：

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "alphaxiv": {
      "type": "remote",
      "url": "https://api.alphaxiv.org/mcp/v1",
      "headers": {
        "Authorization": "Bearer <your-api-key>"
      }
    }
  }
}
```

**Claude Code** — 命令行添加：

```bash
# 使用 API key（推荐，非交互式）
claude mcp add --transport http alphaxiv https://api.alphaxiv.org/mcp/v1 \
  --header "Authorization: Bearer <your-api-key>"

# 或使用 OAuth（交互式，会打开浏览器）
claude mcp add --transport http alphaxiv https://api.alphaxiv.org/mcp/v1
```

### 3. 安全注意事项

- **API key 不要提交到 git。** 配置文件放在全局目录（`~/.config/`）而非项目目录中
- 项目级 `.mimocode/mimocode.json` 可以只写 URL 不写 key，全局配置会自动合并
- 删除 API key 即可立即撤销访问权限

### 4. 验证

重启 agent session，然后测试搜索：

```
搜索论文: LLM agent tool use
```

agent 应调用 `alphaxiv_discover_papers` 返回论文列表。

## 可用的 alphaXiv MCP 工具

| 工具 | 用途 | 典型用法 |
|------|------|----------|
| `discover_papers` | 关键词+语义搜索 | 发现相关论文、文献综述 |
| `get_paper_content` | 获取论文全文/AI 摘要 | 快速阅读论文 |
| `answer_pdf_queries` | 按问题提取特定页面 | 精准提取方法/实验结果 |
| `read_files_from_github_repository` | 读取论文关联 GitHub 代码 | 代码走读前置步骤 |
| `list_library` | 查看文献库 | 管理已读/待读论文 |
| `save_papers_to_folder` | 保存论文到文件夹 | 跟踪阅读进度 |
| `move_papers_between_folders` | 在文件夹间移动论文 | 标记阅读状态 |

## Python 依赖（可选）

脚本工具需要以下 Python 包：

| 包 | 安装 | 用途 |
|---|---|---|
| [markitdown](https://github.com/microsoft/markitdown) | `pip install markitdown` | 非 .md 文件自动转换 |
| [arxiv2md](https://github.com/Linxius/arxiv2md) | `pip install git+https://github.com/Linxius/arxiv2md.git` | arXiv 论文→Markdown（解析 HTML，保留公式，下载图片） |
| [Marker](https://github.com/VikParuchuri/marker) | `pip install marker-pdf` | 复杂学术 PDF |
| [trafilatura](https://github.com/adbar/trafilatura) | `pip install trafilatura` | 网页内容提取 |
