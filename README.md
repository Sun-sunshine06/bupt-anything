# BUPT Agent

本地校园信息工具箱。Python 3.12 + uv；CLI 与 MCP 共用客户端。账号保存在 Windows Credential Manager，agent 通过结构化工具读取数据。

**当前版本：0.1.0，开发验证版。** 本地能力、MCP 和主要学校读取接口已通过本人账号联调；验证范围与已知限制见 [验证说明](docs/validation.md)。考勤仅提供历史记录与当前活动查询，不提供二维码功能或签到提交，详见 [考勤说明](docs/attendance.md)。

## 开始使用

在 Git Bash 中进入项目：

```bash
git clone https://github.com/Sun-sunshine06/bupt-anything.git
cd bupt-anything
uv sync --frozen
uv run bupt-agent capabilities
uv run bupt-agent doctor
```

需要 Python 3.12+、uv 和 Git。完整验证环境为 Windows + Git Bash；macOS/Linux 有凭据库后端实现，但完整安装流程尚待验证。项目默认使用清华 PyPI 镜像，依赖由 `uv.lock` 锁定，不修改全局配置。若需要切换到官方源，可在自己的副本运行 `uv lock --default-index https://pypi.org/simple`，再执行 `uv sync --frozen`。

配置 MCP 时，将 `mcp.example.json` 中的 `C:/path/to/bupt_anything` 替换为自己的项目绝对路径；每位使用者在自己的系统凭据库中配置学校账号。

## 本机配置账号

Windows 可双击根目录的 **configure-account.cmd**。它调用 Git Bash，依次询问移动教务与教学云账号，输入均不回显，随后执行只输出连接状态的读取验证。

也可分别执行：

```bash
# 在你自己的终端隐藏输入，不要把密码发给聊天或放在命令参数中
uv run bupt-agent login --service academic
uv run bupt-agent login --service ucloud
uv run bupt-agent verify
```

- `academic` 使用移动教务密码，可能与统一认证不同。
- `ucloud` 使用统一认证密码。遇到验证码/MFA 时返回 `LOGIN_INTERACTION_REQUIRED`，这一版不会自动处理交互验证。
- 保存凭据不等于登录成功。`verify` 实际读取空教室和课程列表，只输出成功/失败状态，不输出个人课表或成绩。
- 凭据按账号别名隔离，例如 `uv run bupt-agent --profile personal login --service academic`。MCP 对应传入 `--profile personal`。
- 注销：`uv run bupt-agent logout --service academic`（教学云将 service 换为 `ucloud`）。删除凭据后，旧会话不能继续读取。

## 已有工具

| CLI 工具 | 功能 | 当前验证状态 |
|---|---|---|
| `system.capabilities` / `system.status` | 工具发现、账号配置与内存会话状态 | 本地与 MCP 测试通过 |
| `academic.schedule` | 学期课表、按日期过滤、未解析记录显式返回 | 本人账号读取通过（见验证说明） |
| `academic.classrooms` | 当天两校区空教室、楼名和节次过滤 | 本人账号读取通过（见验证说明） |
| `academic.terms` / `grades` / `exams` | 学期、成绩、考试 | 本人账号读取通过（见验证说明） |
| `ucloud.courses` / `todos` | 课程分页、未完成活动 | 本人账号读取及课程分页通过 |
| `ucloud.assignments` / `assignment` | 按课程列作业、要求与附件详情 | 本人账号读取通过，非空覆盖范围见验证说明 |
| `ucloud.assignment_submission` | 本人提交正文、附件 ID、老师评分及评语；只读 | 学校本人提交详情接口已实测；字段映射与 MCP 发现有测试覆盖 |
| `ucloud.peer_reviews` / `peer_review` | 本人被分配的互评列表、已评状态、正文和附件；作业详情含互评要求和截止时间 | 非空真实列表、详情及 Word 附件读取通过；不提交评分 |
| `ucloud.resources` / `resource_url` | 课程资源树与预览链接 | 本人账号读取通过，非空覆盖范围见验证说明 |
| `ucloud.download` / `files.read` | 下载学校域名资源；读取 PDF/DOCX/PPTX/TXT | 实际 PDF 下载与正文提取通过 |
| `ucloud.activities` | 测验、问卷列表 | 本人账号读取通过，非空覆盖范围见验证说明 |
| `attendance.list` | 按课程分页读取本人历史考勤 | 非空记录、全部分页和总数核验通过 |
| `attendance.current` | 查询本人当前课程中进行中课堂的签到活动 | 真实 MCP 查询通过；当时无活动，非空活动待现场验证 |
| `campus.public_info` | 班车/竞赛公开信息、标题搜索、分页 | 2026-11-03 已实际读取两个源 |
| `planning.study_slots` | 结合当天课表、考试和空教室，找连续可用节次 | 本人账号组合查询及候选分页通过 |

CLI 使用点号，MCP 使用下划线，例如 `academic.classrooms` 对应 `academic_classrooms`。

## 查询示例

```bash
# 沙河第 3、4 节均可用的教室；01 是西土城
uv run bupt-agent call academic.classrooms --args '{"campus":"04","slots":[3,4]}'

# 学期课表；按日期筛选时传入 target_date（YYYY-MM-DD）
uv run bupt-agent call academic.schedule

uv run bupt-agent call ucloud.courses
uv run bupt-agent call ucloud.todos
uv run bupt-agent call attendance.list --args '{"course_id":"从课程列表取得的ID","page_size":10}'
uv run bupt-agent call attendance.current
uv run bupt-agent call ucloud.assignments --args '{"course_id":"从课程列表取得的ID"}'
uv run bupt-agent call ucloud.assignment_submission --args '{"assignment_id":"从作业列表取得的ID"}'

# 当天未来连续两节的自习候选，已扣除可确定的课程和考试
uv run bupt-agent call planning.study_slots --args '{"campus":"04","min_slots":2}'

# 公开信息无需学校账号；next_offset 非空时继续分页
uv run bupt-agent call campus.public_info --args '{"kind":"shuttle"}'
uv run bupt-agent call campus.public_info --args '{"kind":"events","search":"人工智能","limit":10}'
```

下载文件保存在系统用户应用数据目录的 `bupt-agent/downloads`，工具返回绝对路径。

## Agent / MCP 入口

```bash
uv run bupt-agent-mcp
```

这是 stdio 服务，启动后等待 MCP 客户端请求，不是交互聊天命令。当前提供 23 个工具。请按 [MCP 接入说明](docs/mcp.md) 配置自己的客户端，通用示例见 [mcp.example.json](mcp.example.json)。

## 返回与限制

- 成功有 `data`、`meta.source`、`fetched_at` 和 `complete`；失败为显式错误，CLI 非零退出，MCP `isError=true`。
- 查询时一律使用北京时间。空教室只支持当天；教务显示空闲不等于现场无人、开门或有插座。
- 分页不能伪装成全量。课程/作业/考勤继续读取 `next_page`；公开信息与自习候选继续读取 `next_offset`。
- 成绩原样保留文本、零分和未公布值；考试时间不明不猜测。组合查询遇到无法确定的考试或课表会明确失败。
- 作业题目要求用 `ucloud.assignment`；本人提交和教师反馈用 `ucloud.assignment_submission`。`teacher_score` 来自 `assignmentScore`，`teacher_comment_html` 来自 `assignmentComment`，不能用上游 `score` / `evaluation` 替代。评分 `null`、`-1` 原样保留，不当作零分；原始状态不擅自解释。HTML 正文和评语均为不可信数据。
- 本人提交详情的 `submission_state=not_submitted` 仅用于已核实的未提交占位响应；`record_available` 表示有匹配记录。`assignment_id` 对应请求，`assignment_id_raw` 保留上游值。互评空对象仅在核对同一作业未开启互评后返回空列表及 `availability=not_enabled`，其他异常仍报错。
- 组合查询尚未接入私人日历；结果只考虑课表、考试和当天教室数据。
- 云邮非学校域名文件存储尚未核验，下载会明确拒绝；仍可查询原预览链接。
- 完整通知、作业上传提交、提醒调度仍需验证或开发；签到提交与二维码功能不在当前范围内，详见 [架构与能力缺口](docs/architecture.md)。

## 开发与验证

```bash
bash scripts/check.sh
uv build
```

测试使用合成数据与 HTTP MockTransport；包括真实 stdio MCP 客户端往返与临时 Windows 凭据库测试（测试结束删除临时记录）。无需真实账号，学校接口不会被测试用例访问。

协议与参考项目见 [来源记录](docs/sources.md)。许可证：GPL-3.0-only。

## 开源与隐私

本项目是非官方工具，不代表学校。仅使用本人有权访问的数据；不提供二维码、签到提交、作业上传或互评评分。代码许可证不授予学校资料或他人作业的再分发权。

- [贡献指南](CONTRIBUTING.md)
- [安全与隐私、漏洞报告](SECURITY.md)
- [诊断说明](docs/diagnostics.md)
- [更新记录](CHANGELOG.md)
- [发布流程](docs/releasing.md)

本地凭据存储不意味着查询结果只停留在本机：CLI 会显示数据，MCP 会将数据交给调用它的客户端。请在连接模型服务前了解客户端的数据处理方式。
