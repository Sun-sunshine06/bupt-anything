import json
import sys
from dataclasses import dataclass, field
from uuid import uuid4

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from .common import AgentError, identifier, require

SERVICES = ("academic", "ucloud")


@dataclass(repr=False)
class Credential:
    username: str
    password: str = field(repr=False)
    revision: str = ""


class CredentialStore:
    """One OS-vault entry per profile/service; never falls back to a plaintext file."""

    def _backend(self):
        if sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring

            return WinVaultKeyring()
        backend = keyring.get_keyring()
        module = type(backend).__module__
        require(
            module.startswith(("keyring.backends.macOS", "keyring.backends.SecretService")),
            "需要系统凭据库（Windows Credential Manager、Keychain 或 Secret Service）。",
            "CREDENTIAL_STORE_UNAVAILABLE",
        )
        return backend

    def _key(self, service: str, profile: str) -> tuple[str, str]:
        require(service in SERVICES, "未知账号系统。")
        return f"bupt-agent/{service}", identifier(profile)

    def load(self, service: str, profile: str = "default") -> Credential:
        vault, key = self._key(service, profile)
        try:
            value = self._backend().get_password(vault, key)
            if not value:
                raise AgentError("NOT_CONFIGURED", f"请在本机运行 login 配置 {service} 账号。")
            return Credential(**json.loads(value))
        except (KeyringError, ValueError, TypeError) as exc:
            raise AgentError("CREDENTIAL_STORE_UNAVAILABLE", "无法读取系统凭据库。") from exc

    def save(self, service: str, profile: str, username: str, password: str) -> None:
        vault, key = self._key(service, profile)
        require(bool(username.strip()) and bool(password), "账号和密码不能为空。")
        value = {"username": username.strip(), "password": password, "revision": uuid4().hex}
        try:
            self._backend().set_password(vault, key, json.dumps(value))
        except KeyringError as exc:
            raise AgentError("CREDENTIAL_STORE_UNAVAILABLE", "无法保存到系统凭据库。") from exc

    def delete(self, service: str, profile: str = "default") -> None:
        vault, key = self._key(service, profile)
        try:
            self._backend().delete_password(vault, key)
        except PasswordDeleteError:
            pass
        except KeyringError as exc:
            raise AgentError("CREDENTIAL_STORE_UNAVAILABLE", "无法删除系统凭据。") from exc
