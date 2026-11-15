import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_real_stdio_tool_discovery_and_call():
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "bupt_agent.server", "--profile", "test-unconfigured"]
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            names = {tool.name for tool in tools}
            assert {
                "academic_classrooms",
                "ucloud_courses",
                "ucloud_notifications",
                "ucloud_upcoming_assignments",
                "ucloud_assignment_submission",
                "attendance_current",
            } <= names
            schema = next(tool.inputSchema for tool in tools if tool.name == "academic_classrooms")
            assert "campus" in schema["properties"]
            removed = {
                "attendance_submit",
                "attendance_qr",
                "qr_parse",
                "qr_decode",
                "qr_generate",
                "qr_build",
            }
            assert removed.isdisjoint(names)
            assert len(names) == 25
            result = await session.call_tool("system_capabilities", {})
            assert not result.isError
            assert len(result.structuredContent["data"]) == 25
            for name in removed:
                result = await session.call_tool(name, {})
                assert result.isError
            result = await session.call_tool("attendance_current", {})
            assert result.isError
