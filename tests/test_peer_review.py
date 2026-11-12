import json
import time

import httpx
import pytest
from conftest import mock_transport

from bupt_agent.common import AgentError
from bupt_agent.session import Session
from bupt_agent.ucloud import UCloud


def client_for(vault, handler):
    client = UCloud(mock_transport(handler), vault)
    client.session = Session("synthetic-token", "revision-1", time.monotonic() + 900, "self")
    return client


def response(data):
    return httpx.Response(200, json={"code": 200, "success": True, "data": data})


@pytest.mark.parametrize("enabled", [0, "0"])
async def test_disabled_peer_review_empty_sentinel(vault, enabled):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path.endswith("evaluation-list"):
            return response({})
        assert request.url.path.endswith("work/detail")
        assert dict(request.url.params) == {"assignmentId": "work"}
        return response(
            {"id": "work", "isOpenEvaluation": enabled, "assignmentMutualEvaluation": {}}
        )

    client = client_for(vault, handler)
    try:
        result = await client.peer_reviews("work")
        assert result["meta"]["complete"]
        assert result["data"] == {
            "items": [],
            "page": 1,
            "page_size": 20,
            "total": 0,
            "next_page": None,
            "has_more": False,
            "availability": "not_enabled",
        }
        assert len(paths) == 2
        detail = await client.assignment("work")
        assert detail["data"]["peer_review"] is None
        assert detail["data"]["peer_review_enabled_raw"] == enabled
    finally:
        await client.http.close()


@pytest.mark.parametrize(
    "detail",
    [
        {"id": "work", "isOpenEvaluation": 1},
        {"id": "work"},
        {"id": "other", "isOpenEvaluation": 0},
        {},
    ],
)
async def test_empty_peer_response_requires_confirmed_disabled_assignment(vault, detail):
    client = client_for(
        vault, lambda r: response({} if r.url.path.endswith("evaluation-list") else detail)
    )
    try:
        with pytest.raises(AgentError) as exc:
            await client.peer_reviews("work")
        assert exc.value.code == "UPSTREAM_SCHEMA_CHANGED"
    finally:
        await client.http.close()


@pytest.mark.parametrize("data", [None, [], {"unexpected": []}, {"records": None}])
async def test_malformed_peer_response_is_not_an_empty_list(vault, data):
    def handler(request):
        assert request.url.path.endswith("evaluation-list")
        return response(data)

    client = client_for(vault, handler)
    try:
        with pytest.raises(AgentError) as exc:
            await client.peer_reviews("work")
        assert exc.value.code == "UPSTREAM_SCHEMA_CHANGED"
    finally:
        await client.http.close()


async def test_peer_list_uses_query_params_and_removes_identity(vault):
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/ykt-site/work/evaluation-list"
        assert dict(request.url.params) == {"assignmentId": "work", "current": "2", "size": "1"}
        assert not request.content
        return response(
            {
                "records": [
                    {
                        "id": "review",
                        "account": "private-account",
                        "realName": "private-name",
                        "score": 0,
                        "isEvaluated": 0,
                        "canEnter": True,
                    }
                ],
                "total": 3,
            }
        )

    client = client_for(vault, handler)
    try:
        result = await client.peer_reviews("work", 2, 1)
        assert result["data"]["next_page"] == 3 and not result["meta"]["complete"]
        assert result["data"]["items"][0]["is_evaluated"] is False
        assert result["data"]["items"][0]["score"] == 0
        assert "private" not in json.dumps(result)
    finally:
        await client.http.close()


@pytest.mark.parametrize(
    "can_enter,review_id,code",
    [
        (False, "mine", "REVIEW_NOT_ACCESSIBLE"),
        (True, "other", "REVIEW_NOT_ASSIGNED"),
    ],
)
async def test_inaccessible_or_unassigned_review_not_requested(vault, can_enter, review_id, code):
    def handler(request):
        assert request.url.path.endswith("evaluation-list")
        return response({"records": [{"id": "mine", "canEnter": can_enter}], "total": 1})

    client = client_for(vault, handler)
    try:
        with pytest.raises(AgentError) as exc:
            await client.peer_review("work", review_id)
        assert exc.value.code == code
    finally:
        await client.http.close()


async def test_peer_detail_only_reads_assigned_work_and_its_files(vault):
    def handler(request):
        path = request.url.path
        assert not any(word in path for word in ("submit", "save"))
        if path.endswith("evaluation-list"):
            return response(
                {"records": [{"id": "mine", "canEnter": True, "isEvaluated": 1}], "total": 1}
            )
        if path.endswith("evaluation-view"):
            assert dict(request.url.params) == {"id": "mine"}
            return response(
                {
                    "assignmentId": "work",
                    "assignmentContent": "<p>sample</p>",
                    "attachmentIds": ["file"],
                    "score": 0,
                    "evaluation": "comment",
                }
            )
        assert path == "/blade-source/resource/list/byId"
        assert dict(request.url.params) == {"resourceIds": "file"}
        return response([{"id": "file", "ext": "docx", "name": "private-name.docx"}])

    client = client_for(vault, handler)
    try:
        result = await client.peer_review("work", "mine")
        assert result["data"]["resources"] == [{"resource_id": "file", "extension": "docx"}]
        assert result["data"]["is_evaluated"] is True
        assert result["data"]["content_html"] == "<p>sample</p>"
        assert "private-name" not in json.dumps(result)
    finally:
        await client.http.close()


async def test_wrong_assignment_response_rejected(vault):
    def handler(request):
        if request.url.path.endswith("evaluation-list"):
            return response({"records": [{"id": "mine", "canEnter": True}], "total": 1})
        return response({"assignmentId": "other", "attachmentIds": []})

    client = client_for(vault, handler)
    try:
        with pytest.raises(AgentError) as exc:
            await client.peer_review("work", "mine")
        assert exc.value.code == "UPSTREAM_SCHEMA_CHANGED"
    finally:
        await client.http.close()
