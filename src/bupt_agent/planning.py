import re
from datetime import date

from .common import now, require, success

SLOT_TIMES = [
    ("08:00", "08:45"),
    ("08:50", "09:35"),
    ("09:50", "10:35"),
    ("10:40", "11:25"),
    ("11:30", "12:15"),
    ("13:00", "13:45"),
    ("13:50", "14:35"),
    ("14:45", "15:30"),
    ("15:40", "16:25"),
    ("16:35", "17:20"),
    ("17:25", "18:10"),
    ("18:30", "19:15"),
    ("19:20", "20:05"),
    ("20:10", "20:55"),
]


def minutes(value):
    h, m = map(int, value.split(":"))
    require(
        (0 <= h < 24 and 0 <= m < 60) or (h == 24 and m == 0),
        "考试时间无法确定。",
        "EXAM_TIME_UNRESOLVED",
    )
    return h * 60 + m


def exam_busy_slots(exams: list, target_date: str) -> set[int]:
    busy = set()
    for exam in exams:
        raw = " ".join(
            str(exam.get(k) or "") for k in ("time_text", "date_text", "start_text", "end_text")
        )
        match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", raw)
        require(match is not None, "存在日期待定的考试，不能保证空闲时间。", "EXAM_TIME_UNRESOLVED")
        day = date(*map(int, match.groups())).isoformat()
        if day != target_date:
            continue
        times = re.findall(r"(?<!\d)(\d{1,2}:\d{2})(?!\d)", raw)
        require(len(times) == 2, "当天考试时间待定，不能保证空闲时间。", "EXAM_TIME_UNRESOLVED")
        start, end = map(minutes, times)
        require(start < end, "考试起止时间无法确定。", "EXAM_TIME_UNRESOLVED")
        for i, (left, right) in enumerate(SLOT_TIMES, 1):
            if start < minutes(right) and minutes(left) < end:
                busy.add(i)
    return busy


def candidate_windows(rooms: list, busy: set[int], count: int, earliest_minute: int):
    candidates = []
    for room in rooms:
        free = set(room["available_slots"]) - busy
        for start in range(1, 16 - count):
            slots = list(range(start, start + count))
            if set(slots).issubset(free) and minutes(SLOT_TIMES[start - 1][0]) >= earliest_minute:
                candidates.append(
                    {
                        "room": room["name"],
                        "slots": slots,
                        "start_time": SLOT_TIMES[start - 1][0],
                        "end_time": SLOT_TIMES[start + count - 2][1],
                        "capacity": room.get("capacity"),
                    }
                )
    return sorted(candidates, key=lambda c: (c["start_time"], c["room"]))


async def study_slots(academic, campus="04", min_slots=2, building=None, offset=0, limit=100):
    require(1 <= min_slots <= 14, "min_slots 应为 1–14。")
    require(offset >= 0 and 1 <= limit <= 100, "offset 应非负，limit 应为 1–100。")
    clock = now()
    today = clock.date().isoformat()
    schedule = await academic.schedule(today)
    require(
        schedule["meta"]["complete"],
        "课表存在未解析项目，不能保证空闲时间。",
        "SCHEDULE_INCOMPLETE",
    )
    exams = await academic.exams()
    busy = {s for course in schedule["data"]["items"] for s in course["slots"]}
    busy |= exam_busy_slots(exams["data"]["items"], today)
    classrooms = await academic.classrooms(campus=campus, building=building)
    require(classrooms["meta"]["complete"], "空教室列表不完整。", "CLASSROOMS_INCOMPLETE")
    current = now()
    require(current.date().isoformat() == today, "查询跨越午夜，请重试。", "DATE_CHANGED")
    # Round up to avoid recommending a period that has already begun this minute.
    earliest = current.hour * 60 + current.minute + (1 if current.second else 0)
    candidates = candidate_windows(classrooms["data"]["rooms"], busy, min_slots, earliest)
    return success(
        {
            "date": today,
            "campus": campus,
            "min_slots": min_slots,
            "candidates": candidates[offset : offset + limit],
            "candidate_count": len(candidates),
            "offset": offset,
            "limit": limit,
            "next_offset": offset + limit if offset + limit < len(candidates) else None,
            "busy_slots": sorted(busy),
        },
        "derived:academic+classrooms",
        complete=offset == 0 and len(candidates) <= limit,
        coverage=["academic_courses", "academic_exams", "today_classrooms"],
        note="不包含私人日历；教室仅按教务数据可用，跨节次区间包含课间休息。",
    )
