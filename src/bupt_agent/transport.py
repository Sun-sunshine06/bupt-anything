import json

import httpx

from .common import AgentError, require


class Transport:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(25, connect=10),
            follow_redirects=False,
            headers={"User-Agent": "BUPT-Agent/0.1 (+local personal client)"},
        )

    async def request(self, method: str, url: str, *, limit: int = 8_000_000, **kwargs):
        try:
            async with self.client.stream(method, url, **kwargs) as response:
                parts, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    require(size <= limit, "上游响应超过大小限制。", "RESPONSE_TOO_LARGE")
                    parts.append(chunk)
                # aiter_bytes() has already decompressed the body. Keeping the upstream
                # Content-Encoding would make Response decode it for a second time.
                headers = httpx.Headers(response.headers.raw)
                for name in ("content-encoding", "content-length", "transfer-encoding"):
                    headers.pop(name, None)
                return httpx.Response(
                    response.status_code, headers=headers, content=b"".join(parts)
                )
        except httpx.TimeoutException as exc:
            raise AgentError("NETWORK_TIMEOUT", "连接超时，请稍后重试。") from exc
        except httpx.HTTPError as exc:
            # Never include request URLs, headers, tickets or response bodies in errors.
            raise AgentError("NETWORK_ERROR", "无法连接数据源。") from exc

    async def json(self, method: str, url: str, *, system: str, **kwargs) -> dict:
        response = await self.request(method, url, **kwargs)
        if response.status_code == 401:
            raise AgentError("AUTH_EXPIRED", "登录会话已失效。")
        if response.status_code == 403:
            raise AgentError("FORBIDDEN", "当前账号无权访问该资源。")
        if response.status_code == 429:
            raise AgentError("RATE_LIMITED", "请求过于频繁，请稍后重试。")
        require(not response.is_redirect, "数据接口返回重定向。", "UPSTREAM_REDIRECT")
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise AgentError("UPSTREAM_SCHEMA_CHANGED", "上游没有返回 JSON 数据。") from exc
        require(isinstance(payload, dict), "上游响应不是对象。", "UPSTREAM_SCHEMA_CHANGED")
        code = str(payload.get("code", ""))
        # SJD's documented HTTP 500 + business 401 is an authentication failure.
        if code == "401" and (
            response.is_success or system == "academic" and response.status_code == 500
        ):
            raise AgentError("AUTH_EXPIRED", "登录会话已失效。")
        require(
            response.is_success, f"数据源返回 HTTP {response.status_code}。", "UPSTREAM_HTTP_ERROR"
        )
        accepted = {"1"} if system == "academic" else {"200", ""}
        require(
            code in accepted and payload.get("success") is not False,
            "数据源返回业务失败，未将其视为空结果。",
            "UPSTREAM_REJECTED",
        )
        return payload

    async def close(self):
        await self.client.aclose()
