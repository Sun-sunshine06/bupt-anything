import time

import httpx
import pytest
from conftest import mock_transport

from bupt_agent.common import AgentError
from bupt_agent.credentials import Credential
from bupt_agent.session import Session
from bupt_agent.signin import BASIC, GOING, Attendance
from bupt_agent.ucloud import UCloud

IDS = {"course_id": "100", "lesson_id": "200", "activity_id": "300"}


def setup(vault, tmp_path, *, going=None, basic=None, total=1):
    requests = []

    def handler(request):
        requests.append(request)
        path = request.url.path
        if path.endswith("/site/list/student/current"):
            current = int(request.url.params["current"])
            records = [{"id": "100", "siteName": "Synthetic course", "teachers": []}]
            data = {"records": records if current == 1 else [], "total": total}
        elif path == GOING:
            data = [{"siteId": "100", "groupId": "200"}] if going is None else going
        elif path == BASIC:
            data = (
                {
                    "attendanceBasicInfo": {
                        "id": "300",
                        "siteId": "100",
                        "groupId": "200",
                        "attendanceBasicStatus": 1,
                        "attendanceStartTime": "2026-11-03 10:00:00",
                        "attendanceEndTime": "",
                    }
                }
                if basic is None
                else basic
            )
        else:
            pytest.fail("Unexpected endpoint")
        return httpx.Response(200, json={"code": 200, "success": True, "data": data})

    client = UCloud(mock_transport(handler), vault)
    client.session = Session("synthetic-token", "revision-1", time.monotonic() + 900, "own-user")
    service = Attendance(client)
    return service, client, requests


async def test_current_returns_bound_ids_and_does_not_submit(vault, tmp_path):
    svc, client, requests = setup(vault, tmp_path)
    try:
        result = await svc.current()
        assert result["meta"]["complete"]
        assert result["data"]["items"][0] == {
            **IDS,
            "course_name": "Synthetic course",
            "status_raw": 1,
            "start_time": "2026-11-03 10:00:00",
            "end_time": "",
            "limit_time_raw": None,
            "server_acceptance": "unknown",
            "signed_in": None,
        }
        assert {r.url.path for r in requests} <= {
            "/ykt-site/site/list/student/current",
            GOING,
            BASIC,
        }
        going = next(r for r in requests if r.url.path == GOING)
        assert going.method == "POST" and going.url.params["siteIds"] == "100"
    finally:
        await client.http.close()


@pytest.mark.parametrize("empty", [{}, []])
async def test_live_empty_sentinel(vault, tmp_path, empty):
    svc, client, requests = setup(vault, tmp_path, going=empty)
    try:
        result = await svc.current()
        assert result["data"]["items"] == [] and result["meta"]["complete"]
        assert all(r.url.path != BASIC for r in requests)
    finally:
        await client.http.close()


@pytest.mark.parametrize("bad", ["", {"unexpected": []}, 0])
async def test_unknown_ongoing_shapes_never_become_empty(vault, tmp_path, bad):
    svc, client, _ = setup(vault, tmp_path, going=bad)
    try:
        with pytest.raises(AgentError, match="结构改变"):
            await svc.current()
    finally:
        await client.http.close()


async def test_basic_failure_is_explicit_partial_result(vault, tmp_path):
    svc, client, requests = setup(vault, tmp_path, basic={"wrong": []})
    try:
        result = await svc.current()
        assert not result["meta"]["complete"] and result["data"]["errors"]
    finally:
        await client.http.close()


async def test_incomplete_course_pagination_fails_closed(vault, tmp_path):
    svc, client, requests = setup(vault, tmp_path, total=101)
    try:
        with pytest.raises(AgentError) as exc:
            await svc.current()
        assert exc.value.code == "QUERY_INCOMPLETE"
        assert all(r.url.path != GOING for r in requests)
    finally:
        await client.http.close()


async def test_all_course_pages_queried_in_bounded_batches(vault, tmp_path):
    pages, batches = [], []

    def handler(request):
        if request.url.path.endswith("/site/list/student/current"):
            page = int(request.url.params["current"])
            pages.append(page)
            ids = range(1, 101) if page == 1 else [101]
            data = {"records": [{"id": str(i), "siteName": "Synthetic"} for i in ids], "total": 101}
        else:
            assert request.url.path == GOING
            batches.append(request.url.params["siteIds"].split(","))
            data = {}
        return httpx.Response(200, json={"code": 200, "success": True, "data": data})

    client = UCloud(mock_transport(handler), vault)
    client.session = Session("synthetic-token", "revision-1", time.monotonic() + 900, "own-user")
    try:
        result = await Attendance(client).current()
        assert result["data"]["queried_courses"] == 101
        assert result["meta"]["complete"]
        assert pages == [1, 2] and [len(b) for b in batches] == [50, 50, 1]
    finally:
        await client.http.close()


async def test_current_rejects_foreign_course_before_activity_query(vault, tmp_path):
    svc, client, requests = setup(vault, tmp_path)
    try:
        with pytest.raises(AgentError) as exc:
            await svc.current("999")
        assert exc.value.code == "COURSE_NOT_ENROLLED"
        assert all(r.url.path not in {GOING, BASIC} for r in requests)
    finally:
        await client.http.close()


async def test_account_changed_during_current_query_does_not_publish(vault, tmp_path):
    svc, client, _ = setup(vault, tmp_path)
    original = svc.basic

    async def changed(*args):
        activity = await original(*args)
        vault.credential = Credential("other", "password", "revision-2")
        return activity

    svc.basic = changed
    try:
        with pytest.raises(AgentError) as exc:
            await svc.current()
        assert exc.value.code == "ACCOUNT_CHANGED"
    finally:
        await client.http.close()
