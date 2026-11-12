import asyncio
import time
from dataclasses import dataclass, field

from .common import AgentError
from .credentials import CredentialStore
from .transport import Transport


@dataclass(repr=False)
class Session:
    token: str = field(repr=False)
    revision: str
    expires_at: float
    user_id: str = ""


class AuthenticatedService:
    service: str

    def __init__(self, transport: Transport, credentials: CredentialStore, profile="default"):
        self.http, self.credentials, self.profile = transport, credentials, profile
        self.session: Session | None = None
        self.lock = asyncio.Lock()

    async def authenticate(self, credential) -> Session:
        raise NotImplementedError

    async def get_session(self) -> Session:
        async with self.lock:
            credential = self.credentials.load(self.service, self.profile)
            if (
                self.session
                and self.session.revision == credential.revision
                and self.session.expires_at > time.monotonic()
            ):
                return self.session
            self.session = None
            session = await self.authenticate(credential)
            current = self.credentials.load(self.service, self.profile)
            if current.revision != credential.revision:
                raise AgentError("ACCOUNT_CHANGED", "登录过程中账号已更改，请重新查询。")
            self.session = session
            return session

    async def call(self, method: str, path: str, **kwargs) -> dict:
        for attempt in range(2):
            session = await self.get_session()
            try:
                result = await self.http.json(
                    method,
                    self.base + path,
                    system=self.service,
                    headers=self.headers(session),
                    **kwargs,
                )
                current = self.credentials.load(self.service, self.profile)
                if current.revision != session.revision:
                    raise AgentError("ACCOUNT_CHANGED", "请求期间账号已更改，结果已丢弃。")
                return result
            except AgentError as error:
                if error.code != "AUTH_EXPIRED" or attempt:
                    raise
                if self.session is session:
                    self.session = None
        raise AssertionError("unreachable")
