"""Read-only discovery of attendance activities in the current user's courses.

Protocol reference: llcc01/ucloud-check, src/req.tsx at
12f128462b5c19b71424073e15a61b03f0ea69b6 (read endpoints only).
"""

from .common import AgentError, identifier, object_data, require, success
from .ucloud import SOURCE

GOING = "/blade-chat/web/chat/myCourse"
BASIC = "/ykt-site/attendancebasicinfo/basic"


class Attendance:
    def __init__(self, ucloud):
        self.client = ucloud

    def unchanged(self, session):
        credential = self.client.credentials.load(self.client.service, self.client.profile)
        require(
            credential.revision == session.revision,
            "查询期间账号已更改，请重新查询。",
            "ACCOUNT_CHANGED",
        )

    async def own_courses(self):
        courses, page, expected_total = {}, 1, None
        while page:
            require(page <= 100, "课程超过查询上限，未将部分课程视为全量。", "QUERY_LIMIT")
            result = await self.client.courses(page=page, page_size=100)
            total = result["data"]["total"]
            if expected_total is not None:
                require(
                    total == expected_total,
                    "课程分页期间总数变化，请重新查询。",
                    "QUERY_INCOMPLETE",
                )
            expected_total = total
            for row in result["data"]["items"]:
                site = identifier(str(row["id"]))
                require(site not in courses, "课程分页包含重复项，请重新查询。", "QUERY_INCOMPLETE")
                courses[site] = row["name"]
            page = result["data"]["next_page"]
        require(
            expected_total is None or len(courses) == expected_total,
            "课程分页数量不完整。",
            "QUERY_INCOMPLETE",
        )
        return courses

    async def basic(self, course_id, lesson_id):
        data = object_data(
            await self.client.call(
                "POST",
                BASIC,
                json={"siteId": course_id, "groupId": lesson_id},
            )
        )
        basic = data.get("attendanceBasicInfo")
        require(
            isinstance(basic, dict) and "id" in basic,
            "签到基础信息结构改变。",
            "UPSTREAM_SCHEMA_CHANGED",
        )
        raw_id = str(basic["id"])
        if raw_id in {"0", "-1", ""}:
            return None
        require(
            raw_id.isdigit() and int(raw_id) > 0,
            "签到活动 ID 格式改变。",
            "UPSTREAM_SCHEMA_CHANGED",
        )
        require(
            str(basic.get("siteId")) == course_id, "签到活动与课程不匹配。", "ACTIVITY_MISMATCH"
        )
        # groupId identifies the current lesson, not the teaching class.
        require(
            str(basic.get("groupId")) == lesson_id, "签到活动与课次不匹配。", "ACTIVITY_MISMATCH"
        )
        return {
            "activity_id": raw_id,
            "course_id": course_id,
            "lesson_id": lesson_id,
            "status_raw": basic.get("attendanceBasicStatus"),
            "start_time": basic.get("attendanceStartTime"),
            "end_time": basic.get("attendanceEndTime"),
            "limit_time_raw": basic.get("attendanceLimitTime"),
            "server_acceptance": "unknown",
            "signed_in": None,
        }

    async def current(self, course_id=None):
        if course_id is not None:
            identifier(course_id)
        session = await self.client.get_session()
        courses = await self.own_courses()
        if course_id is not None:
            require(course_id in courses, "课程不在本人当前课程列表中。", "COURSE_NOT_ENROLLED")
            courses = {course_id: courses[course_id]}
        lessons = []
        course_ids = list(courses)
        # Bound query-string size instead of placing an entire semester in one URL.
        for offset in range(0, len(course_ids), 50):
            batch = course_ids[offset : offset + 50]
            payload = await self.client.call(
                "POST",
                GOING,
                params={"siteIds": ",".join(batch)},
                json={},
            )
            rows = payload.get("data")
            if rows == {}:  # Live-verified school's empty-classroom sentinel.
                rows = []
            require(
                isinstance(rows, list) and all(isinstance(r, dict) for r in rows),
                "进行中课堂响应结构改变。",
                "UPSTREAM_SCHEMA_CHANGED",
            )
            for row in rows:
                site, group = str(row.get("siteId", "")), str(row.get("groupId", ""))
                require(site in batch, "上游返回了范围外课程。", "UPSTREAM_SCHEMA_CHANGED")
                identifier(group)
                require(group not in {"0", "-1"}, "课次 ID 无效。", "UPSTREAM_SCHEMA_CHANGED")
                if (site, group) not in lessons:
                    lessons.append((site, group))
        items, errors, without_activity = [], [], 0
        for site, group in lessons:
            try:
                activity = await self.basic(site, group)
                if activity:
                    items.append({**activity, "course_name": courses[site]})
                else:
                    without_activity += 1
            except AgentError as error:
                if error.code == "ACCOUNT_CHANGED":
                    raise
                errors.append({"course_id": site, "lesson_id": group, "code": error.code})
        self.unchanged(session)
        return success(
            {
                "items": items,
                "queried_courses": len(courses),
                "ongoing_lessons": len(lessons),
                "lessons_without_attendance": without_activity,
                "errors": errors,
            },
            SOURCE,
            complete=not errors,
            note="仅查询本人当前课程；进行中课堂不等于允许签到。状态枚举保留原值，提交资格由学校判定。",
        )
