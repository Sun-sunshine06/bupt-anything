# 考勤只读查询

当前版本仅提供本人历史考勤和当前签到活动查询，不提供二维码解析、识别、生成、服务器时间凭据读取或签到提交。

## 当前活动

```bash
uv run bupt-agent call attendance.current
uv run bupt-agent call attendance.current --args '{"course_id":"课程ID"}'
```

自动读取本人当前课程的全部分页，再按每批最多 50 门查询进行中课堂，读取每个课次的活动基础信息。可按本人课程 ID 过滤。返回活动、课程、课次 ID、课程名称、原始状态和时间。

`errors` 非空或 `meta.complete=false` 表示查询不完整，不能当成没有活动。未知响应结构明确报错；查询期间账号变更会拒绝返回旧账号结果。

活动存在不代表允许签到，也不代表本人已签到。状态枚举保留原值，`signed_in=null`；本工具不执行提交。

## 历史考勤

```bash
uv run bupt-agent call attendance.list --args '{"course_id":"课程ID","page":1,"page_size":10}'
```

只查询当前登录用户的记录，不接受其他用户 ID。按 `next_page` 继续读取；未取完分页时不宣称全量。历史统计不能证明某次当前活动已完成签到。

## 验证与来源

历史考勤非空记录、分页及总数已在本人账号验证。当前活动已验证真实空结果；非空活动的字段和状态枚举仍需现场读取验证。

当前课堂与活动查询参考 `llcc01/ucloud-check` 的 `src/req.tsx`，版本见 [来源记录](sources.md)。保留的只读端点为 `/blade-chat/web/chat/myCourse` 和 `/ykt-site/attendancebasicinfo/basic`。

复查：`uv run --frozen python scripts/live_attendance_readonly.py`。仅输出与保存聚合状态，不保存个人明细或凭据。
