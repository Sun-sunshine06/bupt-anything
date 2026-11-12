import gzip

import httpx
from conftest import mock_transport


async def test_non_ascii_download_header_preserves_raw_bytes():
    headers = [(b"content-disposition", 'attachment; filename="合成资料.pdf"'.encode())]
    transport = mock_transport(lambda _: httpx.Response(200, headers=headers, content=b"%PDF-test"))
    try:
        response = await transport.request("GET", "https://example.test/file")
        assert response.content == b"%PDF-test"
        assert "合成资料" in response.headers["content-disposition"]
    finally:
        await transport.close()


async def test_gzip_response_is_not_decoded_twice():
    body = b'{"code":1,"data":[]}'
    transport = mock_transport(
        lambda _: httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=gzip.compress(body)
        )
    )
    try:
        result = await transport.json("GET", "https://example.test/data", system="academic")
        assert result["data"] == []
    finally:
        await transport.close()
