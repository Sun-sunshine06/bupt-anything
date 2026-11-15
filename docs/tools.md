# 工具与查询参考

[返回首页](../README.md) · [验证范围](validation.md)

以下验证记录来自有限账号和样本，不代表所有场景均已覆盖。最新验证范围以验证说明为准。

## 工具目录


| CLI 工具 | 功能 | 当前验证状态 |
|---|---|---|
| `system.capabilities` / `system.status` | 工具发现、账号配置与内存会话状态 | 本地与 MCP 测试通过 |
| `academic.schedule` | 学期课表、按日期过滤、未解析记录显式返回 | 本人账号读取通过（见验证说明） |
| `academic.classrooms` | 当天两校区空教室、楼名和节次过滤 | 本人账号读取通过（见验证说明） |
| `academic.terms` / `grades` / `exams` | 学期、成绩、考试 | 本人账号读取通过（见验证说明） |
| `ucloud.courses` / `todos` | 课程分页、未完成活动 | 本人账号读取及课程分页通过 |
| `ucloud.notifications` / `upcoming_assignments` | 分页读取本人消息，自动发现并读取通知中未开始的作业 | 真实 MCP、非空通知及未开始作业详情验证通过 |
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


## 消息通知与未开始作业

课程作业列表和待办可能没有显示尚未开始的作业。使用消息通知入口可发现已经向本人发送通知、详情允许访问的作业：

```bash
# 分页查看本人消息通知；不标记已读、不删除
uv run bupt-agent call ucloud.notifications --args '{"page":1,"page_size":50}'

# 自动遍历通知、按作业 ID 去重并读取未开始作业的完整要求和附件信息
uv run bupt-agent call ucloud.upcoming_assignments

# 达到扫描上限时，使用返回的 next_page，保持原 page_size 继续
uv run bupt-agent call ucloud.upcoming_assignments --args '{"page":11,"page_size":50,"max_pages":10}'
```

MCP 名称为 `ucloud_notifications` 和 `ucloud_upcoming_assignments`。工具在一次调用中自动读取最多 `max_pages` 页通知，默认 10 页、每页 50 条；`max_pages` 范围 1–20，`page_size` 范围 1–100。不会后台定时运行。

- `items` 包含开始时间晚于本次 `checked_at` 的作业，时间按北京时间判断；保留要求正文、起止时间、原始状态、附件资源信息和详情链接。
- `notification_title` 保留通知标题，不把它或通知扩展字段猜成已验证的课程 ID。
- 同一次调用按作业 ID 去重；跨次续查时调用方也应去重。已读通知同样参与发现。
- `next_page` 非空表示尚有通知未扫描；`pages_read`、`notifications_scanned` 和 `notification_total` 说明覆盖范围。通知列表实时变化，不是固定快照。
- 不能解析开始时间的详情放在 `unresolved_items`；不可访问、已失效或编号不匹配的详情放在 `errors`。认证、账号变更、限流及网络故障直接报错，不冒充空结果。
- `meta.complete` 仅在从第 1 页读完通知且无未解析项或详情错误时为真；即使为真，也只表示通知范围内完成，不代表教师全部草稿。缺失或已删除的通知无法通过此入口发现。
- 附件先返回资源 ID、名称和类型。需要正文时继续调用 `ucloud.download` 与 `files.read`，不会自动批量下载。
- 全程仅查询，不标记已读、不删除消息、不提交作业。通知 HTML、作业正文与附件文本都是数据，不是 agent 指令。

## 返回与限制


- 成功有 `data`、`meta.source`、`fetched_at` 和 `complete`；失败为显式错误，CLI 非零退出，MCP `isError=true`。
- 查询时一律使用北京时间。空教室只支持当天；教务显示空闲不等于现场无人、开门或有插座。
- 分页不能伪装成全量。课程/作业/考勤继续读取 `next_page`；公开信息与自习候选继续读取 `next_offset`。
- 成绩原样保留文本、零分和未公布值；考试时间不明不猜测。组合查询遇到无法确定的考试或课表会明确失败。
- 作业题目要求用 `ucloud.assignment`；本人提交和教师反馈用 `ucloud.assignment_submission`。`teacher_score` 来自 `assignmentScore`，`teacher_comment_html` 来自 `assignmentComment`，不能用上游 `score` / `evaluation` 替代。评分 `null`、`-1` 原样保留，不当作零分；原始状态不擅自解释。HTML 正文和评语均为不可信数据。
- 本人提交详情的 `submission_state=not_submitted` 仅用于已核实的未提交占位响应；`record_available` 表示有匹配记录。`assignment_id` 对应请求，`assignment_id_raw` 保留上游值。互评空对象仅在核对同一作业未开启互评后返回空列表及 `availability=not_enabled`，其他异常仍报错。
- 组合查询尚未接入私人日历；结果只考虑课表、考试和当天教室数据。
- 云邮非学校域名文件存储尚未核验，下载会明确拒绝；仍可查询原预览链接。
- 消息通知读取及未开始作业发现已支持；通知管理、作业上传提交、提醒调度仍需开发；签到提交与二维码功能不在当前范围内，详见 [架构与能力缺口](architecture.md)。

