import httpx
import pytest
from conftest import mock_transport

from bupt_agent.academic import Academic, expand_weeks, parse_classrooms, parse_schedule
from bupt_agent.common import AgentError, now


def test_classroom_intersection_preserves_unknown_buildings():
    rows = [
        {"NODENAME": "第3节", "CLASSROOMS": "未来新楼-301(80),教1-102(40)"},
        {"NODENAME": "第4节", "CLASSROOMS": "未来新楼-301(80)"},
    ]
    items, unresolved = parse_classrooms(rows, [3, 4], None)
    assert not unresolved
    assert items == [{"name": "未来新楼-301", "capacity": 80, "available_slots": [3, 4]}]


def test_malformed_classrooms_are_not_empty_success():
    with pytest.raises(AgentError, match="字段"):
        parse_classrooms([{"mystery": []}], [], None)


async def test_future_query_never_logs_in(vault):
    def forbidden(_):
        pytest.fail("unsupported date must not send a request")

    transport = mock_transport(forbidden)
    api = Academic(transport, vault)
    with pytest.raises(AgentError) as error:
        await api.classrooms(target_date="2999-01-01")
    assert error.value.code == "UNSUPPORTED_DATE"
    await transport.close()


@pytest.mark.parametrize(
    "http_status,code,expected_logins", [(500, "401", 2), (503, "503", 1), (403, "403", 1)]
)
async def test_only_expired_auth_retries(vault, http_status, code, expected_logins):
    logins, queries = 0, 0

    def respond(request):
        nonlocal logins, queries
        if request.url.path.endswith("/login"):
            logins += 1
            return httpx.Response(200, json={"code": 1, "data": {"token": "private-token"}})
        queries += 1
        if queries == 1:
            return httpx.Response(http_status, json={"code": code})
        return httpx.Response(200, json={"code": 1, "data": []})

    transport = mock_transport(respond)
    api = Academic(transport, vault)
    if expected_logins == 2:
        result = await api.classrooms()
        assert result["data"]["date"] == now().date().isoformat()
    else:
        with pytest.raises(AgentError):
            await api.classrooms()
    assert logins == expected_logins
    await transport.close()


async def test_changed_account_rejects_response(vault):
    def respond(request):
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"code": 1, "data": {"token": "private-token"}})
        vault.credential.revision = "revision-2"
        return httpx.Response(200, json={"code": 1, "data": []})

    transport = mock_transport(respond)
    with pytest.raises(AgentError) as error:
        await Academic(transport, vault).classrooms()
    assert error.value.code == "ACCOUNT_CHANGED"
    await transport.close()


def test_odd_even_weeks_and_unresolved_schedule():
    assert expand_weeks("1-5(单),2-6(双)") == [1, 2, 3, 4, 5, 6]
    assert expand_weeks("待定") == []
    payload = {
        "data": [
            {
                "date": [{"mxrq": "2026-09-07", "zc": "1"}],
                "item": [
                    {
                        "courseName": "合成课程",
                        "classTime": "10304",
                        "weekDay": "1",
                        "classWeek": "1-16",
                    },
                    {"courseName": "待定课程", "classTime": "", "classWeek": "待定"},
                ],
            }
        ]
    }
    data, complete = parse_schedule(payload, "2026-09-07")
    assert data["items"][0]["slots"] == [3, 4]
    assert len(data["unresolved_items"]) == 1
    assert not complete


async def test_zero_and_text_grades_survive(vault):
    def respond(request):
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"code": 1, "data": {"token": "t"}})
        return httpx.Response(
            200,
            json={
                "code": 1,
                "data": [
                    {
                        "pjxfjd": 0,
                        "achievement": [
                            {"courseName": "A", "fraction": 0},
                            {"courseName": "B", "fraction": "优秀"},
                        ],
                    }
                ],
            },
        )

    transport = mock_transport(respond)
    result = await Academic(transport, vault).grades(term="2026-2027-1")
    assert result["data"]["average_grade_point"] == 0
    assert [r["score"] for r in result["data"]["items"]] == [0, "优秀"]
    await transport.close()
