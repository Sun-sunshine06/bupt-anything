"""Read-only current attendance checks through MCP; aggregate output only."""

import json
import sys
from pathlib import Path

from diagnostics import run
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from bupt_agent.common import now


async def main():
    report = {"checked_at": now().isoformat()}
    server = StdioServerParameters(command=sys.executable, args=["-m", "bupt_agent.server"])
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name: t for t in (await session.list_tools()).tools}
            report["tools_discovered"] = all(
                name in tools for name in ("attendance_current", "attendance_list")
            )
            assert tools["attendance_current"].annotations.readOnlyHint is True
            result = await session.call_tool("attendance_current", {})
            assert not result.isError, "Current attendance read failed"
            content = result.structuredContent
            data = content["data"]
            report["current"] = {
                "ok": content["ok"],
                "complete": content["meta"]["complete"],
                "queried_courses": data["queried_courses"],
                "ongoing_lessons": data["ongoing_lessons"],
                "activities": len(data["items"]),
                "errors": len(data["errors"]),
            }
    target = Path(__file__).resolve().parents[1] / "artifacts" / "live-attendance-report.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    run(main)
