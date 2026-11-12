import httpx
import pytest

from bupt_agent.common import AgentError
from bupt_agent.credentials import Credential
from bupt_agent.transport import Transport


class MemoryCredentials:
    def __init__(self, configured=True):
        self.configured = configured
        self.credential = Credential("synthetic-user", "synthetic-password", "revision-1")

    def load(self, service, profile):
        if not self.configured:
            raise AgentError("NOT_CONFIGURED", "未配置测试账号。")
        return self.credential


@pytest.fixture
def vault():
    return MemoryCredentials()


def mock_transport(handler):
    return Transport(
        httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    )
