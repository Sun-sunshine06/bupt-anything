import json
import time

import httpx
import pytest
from conftest import mock_transport

from bupt_agent.app import App
from bupt_agent.session import Session


@pytest.mark.parametrize("score", [5.0, 0, -1, None])
async def test_own_feedback_uses_teacher_fields_and_preserves_score(vault, score):
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/ykt-site/work/submit-view"
        assert dict(request.url.params) == {"assignmentId": "work"}
        assert not request.content
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "assignmentId": "work",
                    "assignmentScore": score,
                    "assignmentComment": "<p>教师评语</p>",
                    "score": 99,
                    "evaluation": "不是教师评语",
                    "assignmentContent": "<p>我的提交</p>",
                    "attachmentIds": [],
                    "assignmentStatus": 1,
                    "status": 0,
                    "userName": "private-name",
                },
            },
        )

    app = App(credentials=vault, transport=mock_transport(handler))
    app.ucloud.session = Session("synthetic", "revision-1", time.monotonic() + 900, "self")
    try:
        result = await app.invoke("ucloud.assignment_submission", {"assignment_id": "work"})
        assert result["ok"]
        assert result["data"]["teacher_score"] == score
        assert result["data"]["teacher_comment_html"] == "<p>教师评语</p>"
        assert result["data"]["attachment_ids"] == []
        assert result["data"]["status_raw"] == 0
        assert result["data"]["submission_state"] == "record_available"
        assert "private-name" not in json.dumps(result)
        assert "不是教师评语" not in json.dumps(result, ensure_ascii=False)
    finally:
        await app.close()


@pytest.mark.parametrize("raw_id,raw_status", [(-1, 99), ("-1", "99")])
async def test_unsubmitted_form_preserves_raw_fields(vault, raw_id, raw_status):
    data = {
        "assignmentId": raw_id,
        "assignmentStatus": raw_status,
        "assignmentContent": "",
        "attachmentIds": [],
        "assignmentScore": -1,
        "assignmentComment": "",
        "status": 3,
    }

    def handler(request):
        assert dict(request.url.params) == {"assignmentId": "work"}
        value = (
            data
            if request.url.path.endswith("submit-view")
            else {
                "id": "work",
                "assignmentStatus": raw_status,
            }
        )
        return httpx.Response(200, json={"code": 200, "data": value})

    app = App(
        credentials=vault,
        transport=mock_transport(handler),
    )
    app.ucloud.session = Session("synthetic", "revision-1", time.monotonic() + 900, "self")
    try:
        result = await app.invoke("ucloud.assignment_submission", {"assignment_id": "work"})
        assert result["ok"]
        assert result["data"]["submission_state"] == "not_submitted"
        assert result["data"]["assignment_id"] == "work"
        assert result["data"]["assignment_id_raw"] == raw_id
        assert result["data"]["assignment_status_raw"] == raw_status
        assert result["data"]["teacher_score"] == -1
    finally:
        await app.close()


@pytest.mark.parametrize(
    "override",
    [
        {"assignmentId": "other"},
        {"assignmentStatus": 0},
        {"assignmentContent": "private content"},
        {"attachmentIds": ["file"]},
        {"attachmentIds": None},
        {"assignmentContent": None},
    ],
)
async def test_inconsistent_unsubmitted_form_is_rejected(vault, override):
    data = {
        "assignmentId": -1,
        "assignmentStatus": 99,
        "assignmentContent": "",
        "attachmentIds": [],
        **override,
    }
    app = App(
        credentials=vault,
        transport=mock_transport(lambda r: httpx.Response(200, json={"code": 200, "data": data})),
    )
    app.ucloud.session = Session("synthetic", "revision-1", time.monotonic() + 900, "self")
    try:
        result = await app.invoke("ucloud.assignment_submission", {"assignment_id": "work"})
        assert not result["ok"]
        assert result["error"]["code"] == "UPSTREAM_SCHEMA_CHANGED"
        assert "private content" not in json.dumps(result)
    finally:
        await app.close()


@pytest.mark.parametrize("data", [None, {}, {"assignmentId": "other"}])
async def test_invalid_submission_response_is_not_success(vault, data):
    transport = mock_transport(lambda r: httpx.Response(200, json={"code": 200, "data": data}))
    app = App(credentials=vault, transport=transport)
    app.ucloud.session = Session("synthetic", "revision-1", time.monotonic() + 900, "self")
    try:
        result = await app.invoke("ucloud.assignment_submission", {"assignment_id": "work"})
        assert not result["ok"]
        assert result["error"]["code"] == "UPSTREAM_SCHEMA_CHANGED"
    finally:
        await app.close()


@pytest.mark.parametrize(
    "detail", [{"id": "other", "assignmentStatus": 99}, {"id": "work", "assignmentStatus": 0}, {}]
)
async def test_unsubmitted_sentinel_requires_matching_assignment(vault, detail):
    def handler(request):
        data = {
            "assignmentId": -1,
            "assignmentStatus": 99,
            "assignmentContent": "",
            "attachmentIds": [],
        }
        if request.url.path.endswith("work/detail"):
            data = detail
        return httpx.Response(200, json={"code": 200, "data": data})

    app = App(credentials=vault, transport=mock_transport(handler))
    app.ucloud.session = Session("synthetic", "revision-1", time.monotonic() + 900, "self")
    try:
        result = await app.invoke("ucloud.assignment_submission", {"assignment_id": "work"})
        assert result["error"]["code"] == "UPSTREAM_SCHEMA_CHANGED"
    finally:
        await app.close()
