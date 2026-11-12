import httpx
from conftest import mock_transport

from bupt_agent.public import query_public


async def test_public_pagination_retains_source_freshness():
    transport = mock_transport(
        lambda _: httpx.Response(
            200,
            json={
                "generated_at": "2026-11-02",
                "status": "stale",
                "items": [{"name": "人工智能A"}, {"name": "人工智能B"}, {"name": "数学"}],
            },
        )
    )
    try:
        result = await query_public(transport, "events", "人工智能", 0, 1)
        assert not result["meta"]["complete"]
        assert result["data"]["matched_total"] == 2
        assert result["data"]["next_offset"] == 1
        assert result["data"]["status"] == "stale"
    finally:
        await transport.close()
