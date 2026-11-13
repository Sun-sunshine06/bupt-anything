# bupt-anything

**让 AI 助手读懂你的北邮课表、作业与校园信息。**

[![检查状态](https://github.com/Sun-sunshine06/bupt-anything/actions/workflows/check.yml/badge.svg?branch=main)](https://github.com/Sun-sunshine06/bupt-anything/actions/workflows/check.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![License: GPL-3.0-only](https://img.shields.io/badge/License-GPL--3.0--only-blue)](LICENSE)

bupt-anything 是面向北京邮电大学的非官方校园工具箱，通过 **MCP** 将移动教务、教学云和校园公开信息接入 AI 客户端，也支持直接在命令行中查询。工具在本机运行，账号保存在系统凭据库中。

[快速开始](#快速开始) · [接入 AI 客户端](#接入-ai-客户端) · [工具参考](docs/tools.md) · [参与贡献](CONTRIBUTING.md)

## 可以做什么

连接支持 MCP 的 AI 客户端后，你可以这样提问：

> “今天沙河有没有连续两节适合自习的空教室？避开我的课和考试。”
>
> “帮我查看教学云待办，再整理这门课的作业要求和附件。”
>
> “查看我这次作业的提交记录，以及老师的评分和评语。”

这些是使用场景示例；实际回答由你使用的 AI 客户端生成，并取决于账号权限与学校接口返回的数据。

| 场景 | 支持的能力 |
| --- | --- |
| 教务查询 | 课表、学期、成绩、考试，以及西土城 / 沙河当天空教室 |
| 课程与作业 | 教学云课程、待办、作业要求、本人提交记录、教师反馈及本人被分配的互评 |
| 课程资料 | 资源列表、预览链接、文件下载，提取 PDF / DOCX / PPTX / TXT 正文 |
| 考勤查询 | 本人历史考勤记录与当前签到活动，只读 |
| 校园与自习 | 班车、竞赛公开信息；结合当天课表、考试和空教室寻找自习时段 |

当前提供 23 个工具，CLI 与 MCP 共用业务逻辑。完整参数可通过 `uv run bupt-agent capabilities` 查看，查询示例与返回约定见 [工具参考](docs/tools.md)。

> **项目状态：早期开发版本。** 已在 Windows + Git Bash 环境验证主要流程；macOS / Linux 已实现凭据库后端，完整使用流程仍待验证。学校接口变化可能影响可用性，具体覆盖范围见 [验证说明](docs/validation.md)。

## 快速开始

需要 [Git](https://git-scm.com/downloads) 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)，项目使用 Python 3.12+。以下命令以 Bash 为例，Windows 用户请在 Git Bash 中运行。

### 1. 安装

```bash
git clone https://github.com/Sun-sunshine06/bupt-anything.git
cd bupt-anything
uv sync --frozen
uv run bupt-agent doctor
```

`uv` 会管理项目虚拟环境，无需手动激活。项目默认使用清华 PyPI 镜像；如需改用官方源，可在自己的副本中执行 `uv lock --default-index https://pypi.org/simple`，再运行 `uv sync --frozen`。

### 2. 配置账号

在自己的终端中输入账号和密码，密码输入不会回显：

```bash
uv run bupt-agent login --service academic
uv run bupt-agent login --service ucloud
uv run bupt-agent verify
```

- `academic`：移动教务账号与密码，密码可能与统一认证不同。
- `ucloud`：教学云使用的统一认证账号与密码。
- `verify`：实际连接服务验证，只输出连接状态。仅使用部分功能时，可只配置对应服务。

Windows 用户也可以双击 [configure-account.cmd](configure-account.cmd) 完成配置，需要 Git Bash 安装在默认位置。不要将密码写入 MCP 配置、命令参数或聊天消息。

### 3. 执行第一次查询

```bash
# 查看课表
uv run bupt-agent call academic.schedule

# 查看教学云待办
uv run bupt-agent call ucloud.todos

# 查询沙河第 3、4 节均空闲的教室
uv run bupt-agent call academic.classrooms --args '{"campus":"04","slots":[3,4]}'
```

CLI 返回结构化 JSON。更多查询见 [工具参考](docs/tools.md)，连接问题见 [诊断说明](docs/diagnostics.md)。

## 接入 AI 客户端

完成账号配置后，将以下内容加入支持 **stdio MCP** 的客户端配置。把 `C:/path/to/bupt-anything` 替换为项目的实际绝对路径；macOS / Linux 使用对应系统路径。

```json
{
  "mcpServers": {
    "bupt-agent": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/path/to/bupt-anything",
        "run",
        "--frozen",
        "bupt-agent-mcp"
      ]
    }
  }
}
```

重新加载客户端后，可让助手调用 `system_capabilities` 查看工具、调用 `system_status` 检查账号配置状态。若客户端找不到 `uv`，将 `command` 改为它的绝对路径。

本项目提供工具服务，聊天界面与模型由客户端提供。多账号配置和连接细节见 [MCP 接入说明](docs/mcp.md)，可复制的配置文件见 [mcp.example.json](mcp.example.json)。

## 使用边界与隐私

- **学校业务操作只读。** 保留当前签到活动查询，不提供二维码生成 / 解析、签到提交、作业提交或互评评分。
- 空教室与自习规划仅支持当天，时间按北京时间处理；规划尚未接入个人日历，教务空闲记录也不保证现场可用。
- 暂不处理验证码 / MFA，不支持扫描文档 OCR；文件下载仅限已核验的学校域名资源。
- 账号保存在系统凭据库中；查询结果会显示在 CLI，或交给调用工具的 MCP 客户端。连接模型服务前，请了解客户端的数据处理方式。

本项目与学校无隶属或背书关系。请仅访问本人有权使用的数据，不要公开账号、成绩、课件或他人作业。更多说明见 [安全与隐私](SECURITY.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [工具参考](docs/tools.md) | 工具目录、查询示例、分页与返回字段 |
| [MCP 接入](docs/mcp.md) | 客户端配置、账号别名与连接说明 |
| [诊断指南](docs/diagnostics.md) | 连接检查、诊断脚本与安全反馈 |
| [验证说明](docs/validation.md) | 已验证场景与尚未覆盖的样本 |
| [架构说明](docs/architecture.md) | 数据流、模块边界与后续扩展 |
| [考勤说明](docs/attendance.md) | 历史记录与当前活动的查询边界 |
| [更新记录](CHANGELOG.md) | 版本变更 |

## 参与贡献

欢迎通过 [Issue](https://github.com/Sun-sunshine06/bupt-anything/issues) 反馈问题、提出功能建议，或提交 Pull Request。环境兼容性、接口适配、测试与文档改进都很有帮助。

```bash
uv sync --frozen
bash scripts/check.sh
uv build
```

默认检查使用合成数据和模拟网络，无需学校账号。提交前请阅读 [贡献指南](CONTRIBUTING.md)；安全漏洞请按 [安全报告流程](SECURITY.md) 私下反馈。维护者发布流程见 [发布说明](docs/releasing.md)。

## 许可证与致谢

本项目采用 [GPL-3.0-only](LICENSE) 许可证。代码许可证不授予学校资料或他人内容的再分发权。

感谢校园开源社区提供的协议研究与工具实践；参考项目、版本和许可证记录见 [来源与致谢](docs/sources.md)。
