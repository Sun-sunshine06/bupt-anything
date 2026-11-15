"""Account-backed MCP read checks; only aggregate results are printed/saved."""

import json
import sys
from pathlib import Path

from diagnostics import run
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from bupt_agent.common import now


async def main():
    report = {"checked_at": now().isoformat(), "checks": []}
    server = StdioServerParameters(command=sys.executable, args=["-m", "bupt_agent.server"])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            report["tool_count"] = len(tools)
            assert len(tools) == 25

            async def call(name, args=None):
                response = await session.call_tool(name, args or {})
                data = response.structuredContent
                item = {
                    "tool": name,
                    "ok": not response.isError,
                    "structured": data is not None,
                    "complete": data.get("meta", {}).get("complete") if data else None,
                }
                report["checks"].append(item)
                print(json.dumps(item), flush=True)
                if response.isError:
                    raise RuntimeError(f"Read check failed: {name}")
                return data

            await call("system_capabilities")
            await call("system_status")
            await call("academic_schedule", {"target_date": now().date().isoformat()})
            await call("academic_classrooms", {"campus": "04", "slots": [3, 4]})
            plans = await call("planning_study_slots", {"campus": "04", "limit": 3})
            if plans["data"]["next_offset"] is not None:
                await call(
                    "planning_study_slots",
                    {"campus": "04", "limit": 3, "offset": plans["data"]["next_offset"]},
                )
            courses = await call("ucloud_courses", {"page_size": 100})
            todos = await call("ucloud_todos")
            task = next((t for t in todos["data"]["items"] if t["type"] == 3), None)
            visible_ids = {str(c["id"]) for c in courses["data"]["items"]}
            course_id = next(
                (t["course_id"] for t in todos["data"]["items"] if t["course_id"] in visible_ids),
                str(courses["data"]["items"][0]["id"]) if visible_ids else None,
            )
            if task:
                await call("ucloud_assignment", {"assignment_id": task["id"]})
                await call("ucloud_assignment_submission", {"assignment_id": task["id"]})
                await call("ucloud_peer_reviews", {"assignment_id": task["id"]})
            else:
                report["assignment_sample"] = "no_assignment_todo"
            if course_id is None:
                report["course_samples"] = "no_current_courses"
                target = Path(__file__).resolve().parents[1] / "artifacts" / "live-mcp-report.json"
                target.parent.mkdir(exist_ok=True)
                target.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                return
            await call("ucloud_resources", {"course_id": course_id})
            count, page, total = 0, 1, None
            while page is not None and page <= 20:
                result = await call(
                    "attendance_list", {"course_id": course_id, "page": page, "page_size": 5}
                )
                count += len(result["data"]["items"])
                total = result["data"]["total"]
                page = result["data"]["next_page"]
            report["attendance_pagination"] = {
                "all_pages_read": page is None,
                "count_matches_total": count == total,
            }
            print(
                json.dumps({"attendance_pagination": report["attendance_pagination"]}), flush=True
            )
            assert page is None and count == total, "Attendance pagination is incomplete"
    target = Path(__file__).resolve().parents[1] / "artifacts" / "live-mcp-report.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run(main)
