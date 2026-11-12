import time

import httpx
import pytest
from conftest import mock_transport

from bupt_agent.academic import parse_schedule
from bupt_agent.session import Session
from bupt_agent.ucloud import UCloud


def test_all_week_schedule_uses_nested_term_metadata():
    payload = {
        "data": [
            {
                "date": [{"mxrq": "", "zc": "all"}],
                "topInfo": [{"semesterId": "2026-2027-1", "today": "2026-11-03", "week": "10"}],
                "item": [
                    {
                        "courseName": "合成课程",
                        "classTime": "20304",
                        "weekDay": "2",
                        "classWeek": "3-18",
                    }
                ],
            }
        ]
    }
    data, complete = parse_schedule(payload, "2026-11-03")
    assert complete
    assert data["term_id"] == "2026-2027-1"
    assert data["term_start"] == "2026-08-31"
    assert data["week"] == 10
    assert len(data["items"]) == 1


async def test_resource_tree_uses_post_with_query_params(vault):
    def respond(request):
        assert request.method == "POST"
        assert request.url.params["siteId"] == "course-1"
        assert request.url.params["userId"] == "user-1"
        assert request.content == b""
        return httpx.Response(200, json={"code": 200, "data": []})

    transport = mock_transport(respond)
    api = UCloud(transport, vault)
    api.session = Session("test-token", vault.credential.revision, time.monotonic() + 100, "user-1")
    try:
        assert (await api.resources("course-1"))["ok"]
    finally:
        await transport.close()


async def test_attendance_is_bound_to_logged_in_user_and_paginated(vault):
    def respond(request):
        import json

        body = json.loads(request.content)
        assert body == {"siteId": "course-1", "userId": "self-user", "current": 1, "size": 2}
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "totalCount": 3,
                    "signCount": 2,
                    "attendanceRate": "0.67",
                    "timeAndStatusList": [
                        {"time": "synthetic-1", "status": 11},
                        {"time": "synthetic-2", "status": 999},
                    ],
                },
            },
        )

    transport = mock_transport(respond)
    api = UCloud(transport, vault)
    api.session = Session("t", vault.credential.revision, time.monotonic() + 100, "self-user")
    try:
        result = await api.attendance_records("course-1", page_size=2)
        assert not result["meta"]["complete"]
        assert result["data"]["next_page"] == 2
        assert [r["status_label"] for r in result["data"]["items"]] == ["正常", "未知"]
        assert result["data"]["items"][1]["status_raw"] == 999
    finally:
        await transport.close()


@pytest.mark.parametrize("missing_id", ["null", -1, "-1", None, 0])
async def test_todo_literal_null_course_is_not_a_callable_id(vault, missing_id):
    transport = mock_transport(
        lambda _: httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "undoneNum": 1,
                    "undoneList": [
                        {"activityId": "1", "type": 2, "siteId": missing_id, "siteName": "null"}
                    ],
                },
            },
        )
    )
    api = UCloud(transport, vault)
    api.session = Session("t", vault.credential.revision, time.monotonic() + 100, "self-user")
    try:
        result = await api.todos()
        assert result["data"]["items"][0]["course_id"] is None
        assert result["meta"]["complete"]
    finally:
        await transport.close()
