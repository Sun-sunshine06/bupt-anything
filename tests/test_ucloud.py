import httpx
import pytest
from conftest import mock_transport

from bupt_agent.common import AgentError
from bupt_agent.ucloud import UCloud, page_data


def test_pagination_does_not_claim_complete():
    page = page_data({"data": {"records": [{"id": "1"}], "total": "2"}}, 1, 1)
    assert page["has_more"]
    assert page["next_page"] == 2
    with pytest.raises(AgentError):
        page_data({"data": {}}, 1, 50)


async def test_cas_password_only_sent_to_auth_host(vault):
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.host == "auth.bupt.edu.cn":
            if request.method == "GET":
                return httpx.Response(
                    200,
                    text='<input name="execution" value="synthetic-execution">',
                    headers={"set-cookie": "CASTGC=test; Path=/authserver/; Secure"},
                )
            return httpx.Response(
                302, headers={"location": "https://ucloud.bupt.edu.cn?ticket=synthetic-ticket"}
            )
        if request.url.path.endswith("/oauth/token"):
            return httpx.Response(200, json={"access_token": "private-token", "user_id": "123"})
        assert request.headers.get("blade-auth") == "private-token"
        return httpx.Response(200, json={"code": 200, "data": {"records": [], "total": 0}})

    transport = mock_transport(respond)
    result = await UCloud(transport, vault).courses()
    assert result["ok"] and result["meta"]["complete"]
    for request in requests:
        if request.url.host != "auth.bupt.edu.cn":
            assert b"synthetic-password" not in request.content
            assert "CASTGC" not in request.headers.get("cookie", "")
    await transport.close()


async def test_untrusted_cas_redirect_never_followed(vault):
    def respond(request):
        if request.method == "GET":
            return httpx.Response(200, text='<input name="execution" value="e">')
        return httpx.Response(302, headers={"location": "https://example.invalid?ticket=secret"})

    transport = mock_transport(respond)
    with pytest.raises(AgentError) as error:
        await UCloud(transport, vault).courses()
    assert error.value.code == "LOGIN_FLOW_CHANGED"
    assert "secret" not in str(error.value)
    await transport.close()
