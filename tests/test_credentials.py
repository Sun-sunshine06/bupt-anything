import sys
from uuid import uuid4

import pytest

from bupt_agent.common import AgentError
from bupt_agent.credentials import CredentialStore


@pytest.mark.skipif(sys.platform != "win32", reason="Windows credential vault integration")
def test_windows_vault_roundtrip_and_delete():
    store = CredentialStore()
    profile = "test-" + uuid4().hex
    try:
        store.save("academic", profile, "synthetic-account", "synthetic-password")
        value = store.load("academic", profile)
        assert value.username == "synthetic-account"
        assert value.password == "synthetic-password"
        revision = value.revision
        store.save("academic", profile, "synthetic-account", "replacement")
        assert store.load("academic", profile).revision != revision
    finally:
        store.delete("academic", profile)
    with pytest.raises(AgentError) as error:
        store.load("academic", profile)
    assert error.value.code == "NOT_CONFIGURED"
