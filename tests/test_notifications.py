import json
import time
from datetime import datetime

import httpx
import pytest
from conftest import mock_transport

from bupt_agent.app import App
from bupt_agent.common import SHANGHAI, AgentError
from bupt_agent.session import Session
from bupt_agent.ucloud import UCloud


def notice(assignment_id="101", **extra):
    return {
        "id": "901",
        "objectId": assignment_id,
        "newsModel": "assignment",
        "newsUrl": "To-Be-Student-Publish-Assignment",
        "newsTitle": "Synthetic course",
        "newsInfo": "<span>Synthetic assignment</span>",
        "isRead": 0,
        "newsCopyPersonId": "private-recipient",
        "personIds": "private-list",
        **extra,
    }


def client(vault, handler):
    api = UCloud(mock_transport(handler), vault)
    api.session = Session("synthetic-token", "revision-1", time.monotonic() + 900, "123")
    return api


def reply(data):
    return httpx.Response(200, json={"code": 200, "data": data})


def freeze(monkeypatch):
    monkeypatch.setattr("bupt_agent.ucloud.now", lambda: datetime(2026, 1, 1, tzinfo=SHANGHAI))


async def test_notifications_personal_scope_pagination_and_no_writes(vault):
    def respond(request):
        assert request.method == "POST"
        assert request.url.path == "/ykt-basics/api/inform/news/list"
        assert dict(request.url.params) == {"newsCopyPersonId": "123", "current": "1", "size": "2"}
        return reply({"records": [notice(), notice(newsModel="forum")], "total": 3})

    api = client(vault, respond)
    try:
        result = await api.notifications(page_size=2)
        assert result["data"]["next_page"] == 2
        assert not result["meta"]["complete"]
        assert result["data"]["items"][0]["assignment_id"] == "101"
        assert result["data"]["items"][1]["assignment_id"] is None
        assert "private-" not in json.dumps(result)
        assert result["data"]["items"][0]["read_raw"] == 0
    finally:
        await api.http.close()


async def test_discovery_reads_all_pages_deduplicates_and_uses_start_time(vault, monkeypatch):
    freeze(monkeypatch)
    calls = []

    def respond(request):
        if request.url.path.endswith("/news/list"):
            page = int(request.url.params["current"])
            rows = [notice(), notice()] if page == 1 else [notice("102"), notice("103")]
            return reply({"records": rows, "total": 4})
        assert request.method == "GET" and request.url.path == "/ykt-site/work/detail"
        aid = request.url.params["assignmentId"]
        calls.append(aid)
        start = {"101": "2026-01-02 00:00", "102": "2026-01-01 00:00:00", "103": "unknown"}[aid]
        return reply(
            {
                "id": aid,
                "assignmentTitle": "Synthetic",
                "assignmentBeginTime": start,
                "assignmentStatus": 99,
                "assignmentContent": "<p>requirements</p>",
                "assignmentResource": [{"resourceId": "501", "resourceType": "docx"}],
            }
        )

    api = client(vault, respond)
    try:
        result = await api.upcoming_assignments(page_size=2)
        data = result["data"]
        assert calls == ["101", "102", "103"]
        assert data["pages_read"] == 2 and data["notifications_scanned"] == 4
        assert data["next_page"] is None
        assert [x["id"] for x in data["items"]] == ["101"]
        assert data["items"][0]["content_html"] == "<p>requirements</p>"
        assert data["items"][0]["resources"][0]["resourceId"] == "501"
        assert data["unresolved_items"][0]["assignment_id"] == "103"
        assert not result["meta"]["complete"]
    finally:
        await api.http.close()


async def test_discovery_page_budget_and_continuation(vault, monkeypatch):
    freeze(monkeypatch)

    def respond(request):
        if request.url.path.endswith("/news/list"):
            page = int(request.url.params["current"])
            return reply({"records": [notice(str(100 + page))], "total": 2})
        return reply(
            {"id": request.url.params["assignmentId"], "assignmentBeginTime": "2027-01-01 00:00"}
        )

    api = client(vault, respond)
    try:
        first = await api.upcoming_assignments(page_size=1, max_pages=1)
        assert first["data"]["next_page"] == 2 and not first["meta"]["complete"]
        second = await api.upcoming_assignments(page=2, page_size=1, max_pages=1)
        assert second["data"]["next_page"] is None and not second["meta"]["complete"]
        full = await api.upcoming_assignments(page_size=1)
        assert full["meta"]["complete"] and len(full["data"]["items"]) == 2
    finally:
        await api.http.close()


@pytest.mark.parametrize("failure", ["forbidden", "mismatched_id", "business_rejected"])
async def test_unavailable_details_are_explicit_partial_results(vault, monkeypatch, failure):
    freeze(monkeypatch)

    def respond(request):
        if request.url.path.endswith("/news/list"):
            return reply({"records": [notice()], "total": 1})
        if failure == "forbidden":
            return httpx.Response(403)
        if failure == "business_rejected":
            return httpx.Response(200, json={"code": 500, "msg": "private-response"})
        return reply({"id": "999", "assignmentBeginTime": "2027-01-01 00:00"})

    api = client(vault, respond)
    try:
        result = await api.upcoming_assignments()
        assert not result["meta"]["complete"]
        assert result["data"]["errors"][0]["assignment_id"] == "101"
        assert not result["data"]["items"]
        assert "private-response" not in json.dumps(result)
    finally:
        await api.http.close()


@pytest.mark.parametrize("records", [None, [notice(None)], [notice("null")]])
async def test_notification_schema_changes_fail(vault, records):
    api = client(vault, lambda request: reply({"records": records, "total": 1}))
    try:
        with pytest.raises(AgentError, match=".") as error:
            await api.notifications()
        assert error.value.code == "UPSTREAM_SCHEMA_CHANGED"
    finally:
        await api.http.close()


async def test_account_change_discards_aggregate(vault, monkeypatch):
    freeze(monkeypatch)

    def respond(request):
        if request.url.path.endswith("/news/list"):
            return reply({"records": [notice()], "total": 1})
        vault.configured = False
        return reply({"id": "101", "assignmentBeginTime": "2027-01-01 00:00"})

    api = client(vault, respond)
    try:
        with pytest.raises(AgentError) as error:
            await api.upcoming_assignments()
        assert error.value.code == "NOT_CONFIGURED"
    finally:
        await api.http.close()


async def test_new_tools_validation_and_registration(vault):
    app = App(credentials=vault)
    try:
        for name in ("ucloud.notifications", "ucloud.upcoming_assignments"):
            assert next(t for t in app.catalogue() if t["name"] == name)["read_only"]
            assert (await app.invoke(name, {"page_size": 0}))["error"]["code"] == "INVALID_INPUT"
        assert (await app.invoke("ucloud.upcoming_assignments", {"max_pages": 0}))["error"][
            "code"
        ] == "INVALID_INPUT"
    finally:
        await app.close()
