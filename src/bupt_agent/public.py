from .common import require, success

SOURCES = {
    "shuttle": "https://where-to-study.cn/api/shuttle-bus",
    "events": "https://nemoyuzx.github.io/contest-ddl/data/competitions.json",
}


async def query_public(transport, kind: str, search: str = "", offset: int = 0, limit: int = 30):
    # URLs are registered only after verifying their exact upstream spelling.
    require(kind in SOURCES, "公开信息类型不支持。")
    require(0 <= offset and 1 <= limit <= 100, "offset 应非负，limit 应为 1–100。")
    response = await transport.request("GET", SOURCES[kind], limit=4_000_000)
    require(response.is_success, "公开数据源不可用或返回重定向。", "PUBLIC_SOURCE_UNAVAILABLE")
    try:
        data = response.json()
    except ValueError:
        require(False, "公开数据源未返回 JSON。", "UPSTREAM_SCHEMA_CHANGED")
    require(
        isinstance(data, dict) and isinstance(data.get("items"), list),
        "公开数据缺少 items 集合。",
        "UPSTREAM_SCHEMA_CHANGED",
    )
    rows = data["items"]
    require(all(isinstance(r, dict) for r in rows), "公开条目结构改变。", "UPSTREAM_SCHEMA_CHANGED")
    if search:
        rows = [
            r
            for r in rows
            if search.casefold() in str(r.get("name", r.get("title", ""))).casefold()
        ]
    total = len(rows)
    more = offset + limit < total
    result = {
        **data,
        "items": rows[offset : offset + limit],
        "matched_total": total,
        "offset": offset,
        "limit": limit,
        "next_offset": offset + limit if more else None,
    }
    return success(
        result,
        SOURCES[kind],
        complete=offset == 0 and not more,
        schema="upstream_public_json",
        note="第三方整理信息；fetched_at 是抓取时间，不是来源更新时间。",
    )
