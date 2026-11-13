# 让校园信息，接入你的 AI 助手。

<div class="hero" markdown>

<span class="eyebrow">BUPT-ANYTHING · 开源校园工具箱</span>

从今天的课表，到下一份作业。**bupt-anything** 为北京邮电大学（北邮，BUPT）提供本地 MCP Server 与命令行工具，把移动教务、教学云和校园公开信息连接到你使用的 AI 客户端。

[开始使用 →](getting-started.md){ .md-button .md-button--primary }
[接入 MCP](mcp.md){ .md-button }

<span class="hero-note">Python 3.12+ · 本机运行 · 学校业务只读 · GPL-3.0-only</span>

</div>

## 从一个真实问题开始

<div class="grid cards" markdown>

- **今天在哪里自习？**

    结合当天课表、考试与沙河 / 西土城空教室，寻找连续可用的节次。

    [查看教务与自习工具 →](tools.md)

- **这门课还有什么要做？**

    查询教学云课程、待办、作业要求、本人提交记录和教师反馈。

    [了解教学云查询 →](tools.md)

- **课程资料讲了什么？**

    获取资源列表、下载学校域名资料，提取 PDF、Word、PowerPoint 与文本正文。

    [查看资料读取边界 →](faq.md)

</div>

这些是使用场景示例。实际回答由客户端的模型生成，取决于学校接口数据和你的访问权限。CLI 也可以独立查询，不需要连接 AI。

## 选择你的入口

| 你想做什么 | 从这里开始 |
| --- | --- |
| 第一次安装并配置学校账号 | [安装与首次查询](getting-started.md) |
| 让已有的 AI 客户端调用工具 | [MCP 客户端接入](mcp.md) |
| 查找工具、参数与查询示例 | [工具参考](tools.md) |
| 了解账号、隐私与只读范围 | [常见问题](faq.md) · [安全说明](../SECURITY.md) |
| 排查连接失败或参与开发 | [诊断指南](diagnostics.md) · [贡献指南](../CONTRIBUTING.md) |
| Read a concise English introduction | [English overview](overview.en.md) |

## 项目事实与当前状态

bupt-anything 是**非官方、早期开发中的开源项目**，与北京邮电大学无隶属或背书关系。BUPT Agent 是同一项目的工具名称；CLI 命令为 `bupt-agent`，MCP 服务入口为 `bupt-agent-mcp`。

- **23 个工具**，覆盖教务、教学云、资料、考勤只读查询和校园公开信息。
- **Windows + Git Bash 已验证主要流程**；macOS / Linux 凭据后端已实现，完整使用体验仍待验证。
- **不提供签到、作业或互评提交**，也不提供二维码解析与生成。
- **本地存储凭据不等于数据只留在本地**：MCP 查询结果会进入调用它的客户端。

[查看真实验证范围](validation.md) · [查看版本变更](../CHANGELOG.md) · [查看源码](https://github.com/Sun-sunshine06/bupt-anything)

本页介绍项目已实现的能力；具体限制以工具参考和验证说明为准。学校接口变化可能影响可用性。
