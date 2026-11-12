"""Read-only account integration smoke test. Prints schemas/counts, never personal rows."""

import json
from pathlib import Path

from diagnostics import run, summary

from bupt_agent.app import App
from bupt_agent.common import now


async def main():
    app = App()
    report = {"checked_at": now().isoformat(), "checks": []}

    async def check(name, args=None):
        result = await app.invoke(name, args)
        item = summary(name, result)
        report["checks"].append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
        return result

    try:
        await check("academic.classrooms", {"campus": "01", "slots": [3, 4]})
        await check("academic.classrooms", {"campus": "04", "slots": [3, 4]})
        await check("academic.terms")
        await check("academic.schedule")
        await check("academic.schedule", {"target_date": now().date().isoformat()})
        await check("academic.grades")
        await check("academic.exams")
        await check("planning.study_slots", {"campus": "04"})
        courses, page = [], 1
        while page is not None and page <= 10:
            result = await check("ucloud.courses", {"page": page, "page_size": 5})
            if not result["ok"]:
                break
            courses.extend(result["data"]["items"])
            page = result["data"]["next_page"]
        await check("ucloud.todos")
        inspected_detail = False
        for course in courses[:4]:
            course_id = str(course["id"])
            assignments = await check(
                "ucloud.assignments", {"course_id": course_id, "page_size": 5}
            )
            if assignments["ok"] and assignments["data"]["items"] and not inspected_detail:
                await check(
                    "ucloud.assignment",
                    {"assignment_id": str(assignments["data"]["items"][0]["id"])},
                )
                inspected_detail = True
            await check("ucloud.resources", {"course_id": course_id})
        if courses:
            course_id = str(courses[0]["id"])
            await check("ucloud.activities", {"course_id": course_id, "kind": "quiz"})
            await check("ucloud.activities", {"course_id": course_id, "kind": "survey"})
    finally:
        await app.close()
        target = Path(__file__).resolve().parents[1] / "artifacts" / "live-report.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return 1 if any(not item["ok"] for item in report["checks"]) else 0


if __name__ == "__main__":
    run(main)
