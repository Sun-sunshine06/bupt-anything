from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def now() -> datetime:
    return datetime.now(SHANGHAI)


class AgentError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


def require(condition: bool, message: str, code: str = "INVALID_INPUT") -> None:
    if not condition:
        raise AgentError(code, message)


def success(data: Any, source: str, *, complete: bool = True, **meta: Any) -> dict:
    return {
        "ok": True,
        "data": data,
        "meta": {
            "source": source,
            "fetched_at": now().isoformat(),
            "complete": complete,
            "cached": False,
            **meta,
        },
    }


def failure(error: AgentError) -> dict:
    return {"ok": False, "error": {"code": error.code, "message": error.message}}


def object_data(payload: dict) -> dict:
    data = payload.get("data")
    require(isinstance(data, dict), "上游 data 不是对象。", "UPSTREAM_SCHEMA_CHANGED")
    return data


def list_data(payload: dict) -> list:
    data = payload.get("data")
    require(isinstance(data, list), "上游 data 不是列表。", "UPSTREAM_SCHEMA_CHANGED")
    return data


def pick(row: dict, mapping: dict[str, str]) -> dict:
    return {name: row.get(key) for name, key in mapping.items()}


def identifier(value: str) -> str:
    require(isinstance(value, str) and 0 < len(value) <= 128, "ID 必须是非空字符串。")
    require(all(c.isalnum() or c in "_-" for c in value), "ID 包含不支持的字符。")
    return value
