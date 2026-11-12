import re
import time
from datetime import date, timedelta
from hashlib import sha256

from .common import AgentError, list_data, now, pick, require, success
from .session import AuthenticatedService, Session

BASE = "https://jwglweixin.bupt.edu.cn/bjyddx"
SOURCE = "https://jwglweixin.bupt.edu.cn/sjd/"
CAMPUSES = {"01": "西土城", "04": "沙河"}


def expand_weeks(text: str) -> list[int]:
    weeks = set()
    for segment in re.split(r"[,，、;；]", text.replace(" ", "")):
        match = re.fullmatch(
            r"(\d+)(?:[-~—至](\d+))?(?:周)?(?:[（(]?([单双])[）)]?)?(?:周)?", segment
        )
        if not match:
            return []
        start, end = int(match[1]), int(match[2] or match[1])
        if not 1 <= start <= end <= 60:
            return []
        weeks.update(
            w
            for w in range(start, end + 1)
            if not match[3] or w % 2 == (1 if match[3] == "单" else 0)
        )
    return sorted(weeks)


def walk_courses(value, depth=0):
    require(depth <= 40, "课表嵌套层级超限。", "UPSTREAM_SCHEMA_CHANGED")
    if isinstance(value, dict):
        if "courseName" in value or "jx0408id" in value:
            yield value
        else:
            for child in value.values():
                yield from walk_courses(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            yield from walk_courses(child, depth + 1)


def term_id(root: dict):
    top = root.get("topInfo")
    top = top[0] if isinstance(top, list) and top and isinstance(top[0], dict) else {}
    return (
        root.get("semesterId")
        or root.get("xnxq01id")
        or top.get("semesterId")
        or top.get("xnxq01id")
    )


def infer_term_start(root: dict):
    for item in root.get("date", []):
        if not isinstance(item, dict) or not item.get("mxrq"):
            continue
        try:
            week = int(item.get("zc", root.get("week", 0)))
            if not 1 <= week <= 60:
                continue
            day = date.fromisoformat(item["mxrq"])
            return day - timedelta(days=(week - 1) * 7 + day.weekday())
        except (ValueError, TypeError):
            continue
    top = root.get("topInfo")
    if isinstance(top, list) and top and isinstance(top[0], dict):
        try:
            week = int(top[0].get("week", 0))
            day = date.fromisoformat(top[0].get("today", ""))
            if 1 <= week <= 60:
                return day - timedelta(days=(week - 1) * 7 + day.weekday())
        except (ValueError, TypeError):
            pass
    return None


def parse_schedule(payload: dict, target_date: str | None = None) -> tuple[dict, bool]:
    data = list_data(payload)
    require(
        bool(data) and isinstance(data[0], dict), "课表缺少学期信息。", "UPSTREAM_SCHEMA_CHANGED"
    )
    root = data[0]
    require("item" in root or "courses" in root, "课表缺少课程集合。", "UPSTREAM_SCHEMA_CHANGED")
    term_start = infer_term_start(root)
    target = date.fromisoformat(target_date) if target_date else None
    require(
        not target or term_start is not None,
        "无法确定教学周起点，不能按日期过滤。",
        "TERM_START_UNKNOWN",
    )
    week = ((target - term_start).days // 7 + 1) if target else None
    items, uncertain, seen = [], [], set()
    for row in walk_courses(root.get("item", root.get("courses"))):
        class_time = str(row.get("classTime", ""))
        slots = [int(n) for n in re.findall(r"\d{2}", class_time[1:])]
        if not slots:
            slots = [int(n) for n in re.findall(r"\d+", str(row.get("weekNoteDetail", "")))]
        try:
            weekday = int(str(row.get("weekDay", class_time))[:1])
        except ValueError:
            weekday = 0
        week_text = str(row.get("classWeek") or row.get("classWeekDetails") or "")
        weeks = expand_weeks(week_text)
        item = pick(
            row,
            {
                "course_id": "jx0408id",
                "name": "courseName",
                "teacher": "teacherName",
                "building": "buildingName",
                "room": "classroomName",
            },
        )
        item.update(weekday=weekday, slots=slots, weeks=weeks, week_text=week_text)
        item["id"] = sha256(repr(sorted(item.items())).encode()).hexdigest()[:20]
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        if not weeks or not slots or not 1 <= weekday <= 7 or not all(1 <= s <= 14 for s in slots):
            uncertain.append(item)
        elif not target or (week in weeks and target.isoweekday() == weekday):
            items.append(item)
    return {
        "term_id": term_id(root),
        "term_start": term_start.isoformat() if term_start else None,
        "date": target_date,
        "week": week,
        "items": items,
        "unresolved_items": uncertain,
    }, not uncertain


def parse_classrooms(rows: list, slots: list[int], building: str | None):
    rooms, unresolved = {}, []
    for row in rows:
        require(isinstance(row, dict), "教室记录不是对象。", "UPSTREAM_SCHEMA_CHANGED")
        node = row.get("NODENAME", row.get("nodeName", row.get("nodename")))
        raw = row.get("CLASSROOMS", row.get("classrooms", row.get("Classrooms")))
        require(
            node is not None and isinstance(raw, str),
            "教室字段不符合预期。",
            "UPSTREAM_SCHEMA_CHANGED",
        )
        match = re.search(r"\d+", str(node))
        if not match or not 1 <= int(match[0]) <= 14:
            unresolved.append({"node": str(node)})
            continue
        slot = int(match[0])
        for name in re.split(r"[,，]", raw):
            name = name.strip()
            if not name:
                continue
            size = re.search(r"[（(](\d+)[）)]", name)
            label = re.sub(r"[（(]\d+[）)]", "", name).strip()
            if building and building.casefold() not in label.casefold():
                continue
            room = rooms.setdefault(
                label,
                {"name": label, "capacity": int(size[1]) if size else None, "available_slots": []},
            )
            room["available_slots"].append(slot)
    items = []
    for room in rooms.values():
        room["available_slots"] = sorted(set(room["available_slots"]))
        if set(slots).issubset(room["available_slots"]):
            items.append(room)
    return sorted(items, key=lambda r: r["name"]), unresolved


class Academic(AuthenticatedService):
    service, base = "academic", BASE

    def headers(self, session):
        return {
            "token": session.token,
            "Origin": "https://jwglweixin.bupt.edu.cn",
            "Referer": SOURCE,
        }

    async def authenticate(self, credential):
        try:
            result = await self.http.json(
                "POST",
                BASE + "/login",
                system="academic",
                data={"userNo": credential.username, "pwd": credential.password},
            )
        except AgentError as e:
            if e.code in {"AUTH_EXPIRED", "UPSTREAM_REJECTED"}:
                raise AgentError("LOGIN_FAILED", "移动教务登录失败，请在本机核对教务密码。") from e
            raise
        data = result.get("data")
        require(
            isinstance(data, dict) and bool(data.get("token")), "登录响应缺少令牌。", "LOGIN_FAILED"
        )
        return Session(str(data["token"]), credential.revision, time.monotonic() + 900)

    async def classrooms(self, campus="04", slots=None, building=None, target_date=None):
        require(campus in CAMPUSES, "校区应为 01（西土城）或 04（沙河）。")
        slots = slots or []
        require(all(type(s) is int and 1 <= s <= 14 for s in slots), "节次应为 1–14 的整数。")
        today = now().date().isoformat()
        require(
            target_date is None or target_date == today,
            "该空教室数据源仅支持北京时间当天查询。",
            "UNSUPPORTED_DATE",
        )
        rows = list_data(await self.call("GET", "/todayClassrooms", params={"campusId": campus}))
        items, unresolved = parse_classrooms(rows, slots, building)
        return success(
            {
                "date": today,
                "campus": campus,
                "campus_name": CAMPUSES[campus],
                "requested_slots": slots,
                "rooms": items,
                "unresolved_items": unresolved,
            },
            SOURCE,
            complete=not unresolved,
            availability_basis="教务空教室数据；不代表现场无人或已开门",
        )

    async def schedule(self, target_date=None):
        result = await self.call("POST", "/student/curriculum", params={"week": "all"})
        roots = list_data(result)
        if roots and isinstance(roots[0], dict) and infer_term_start(roots[0]) is None:
            current = list_data(await self.call("POST", "/student/curriculum", params={"week": ""}))
            if current and isinstance(current[0], dict):
                all_term = term_id(roots[0])
                current_term = term_id(current[0])
                require(
                    all_term == current_term and all_term is not None,
                    "无法确认课表元数据属于同一学期。",
                    "TERM_START_UNKNOWN",
                )
                roots[0]["date"] = current[0].get("date", [])
                roots[0]["week"] = current[0].get("week")
        data, complete = parse_schedule(result, target_date)
        return success(data, SOURCE, complete=complete)

    async def terms(self):
        rows = list_data(await self.call("POST", "/semesterList"))
        return success(
            [pick(r, {"id": "semesterId", "name": "semesterName"}) for r in rows], SOURCE
        )

    async def current_term(self):
        rows = list_data(await self.call("POST", "/currentTerm"))
        require(
            bool(rows) and bool(rows[0].get("semesterId")),
            "当前学期缺失。",
            "UPSTREAM_SCHEMA_CHANGED",
        )
        return str(rows[0]["semesterId"])

    async def grades(self, term=None, records="best"):
        require(records in {"best", "first", "all"}, "records 应为 best、first 或 all。")
        term = await self.current_term() if term is None else term
        rows = list_data(
            await self.call(
                "POST",
                "/student/termGPA",
                params={"semester": term, "type": {"best": "1", "first": "0", "all": ""}[records]},
            )
        )
        items, gpa = [], None
        for row in rows:
            require(
                isinstance(row, dict) and isinstance(row.get("achievement"), list),
                "成绩集合结构改变。",
                "UPSTREAM_SCHEMA_CHANGED",
            )
            if row.get("pjxfjd") is not None:
                gpa = row["pjxfjd"]
            items.extend(
                pick(
                    r,
                    {
                        "name": "courseName",
                        "score": "fraction",
                        "credits": "credit",
                        "course_code": "kcbh",
                        "semester": "curSemesterName",
                        "status": "cjbs",
                    },
                )
                for r in row["achievement"]
            )
        return success(
            {"term": term, "record_type": records, "average_grade_point": gpa, "items": items},
            SOURCE,
        )

    async def exams(self, term=None):
        params = {} if term is None else {"semester": term}
        rows = list_data(await self.call("POST", "/student/examinationArrangement", params=params))
        items = [
            pick(
                r,
                {
                    "name": "courseName",
                    "place": "examinationPlace",
                    "time_text": "time",
                    "date_text": "ksqssj",
                    "start_text": "zssj1",
                    "end_text": "zssj2",
                },
            )
            for r in rows
        ]
        return success(
            {"term": term, "items": items},
            SOURCE,
            note="保留源站时间文本；未公布时间不推测为具体节次。",
        )
