import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from outline_mcp.client import Client, parse_doc_ref
from outline_mcp.types import Result


@pytest.mark.asyncio
async def test_call_success():
    client = Client("https://outline.example.com", "test_key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "results": [{"title": "Test", "url": "/doc/test", "snippet": "test"}]
        }
    }

    with patch.object(client.http, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.call("documents.search", {"query": "test"})

    assert result.ok is True
    assert result.error == ""
    assert result.data is not None


@pytest.mark.asyncio
async def test_call_401_unauthorized():
    client = Client("https://outline.example.com", "bad_key")

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": "Invalid token"}

    with patch.object(client.http, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await client.call("documents.search", {})

    assert result.ok is False
    assert "bad_key" not in result.error  # Key redacted
    assert "Outline rejected" in result.error


@pytest.mark.asyncio
async def test_call_timeout():
    client = Client("https://outline.example.com", "test_key")
    client.timeout_ms = 100

    with patch.object(client.http, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("timeout")
        result = await client.call("documents.search", {})

    assert result.ok is False


@pytest.mark.asyncio
async def test_call_no_credentials():
    client = Client("", "")
    result = await client.call("documents.search", {})

    assert result.ok is False
    assert "OUTLINE_API_URL" in result.error


UUID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.parametrize("raw,kind,id_", [
    (UUID, "uuid", UUID),
    ("a1B2c3D4e5", "urlId", "a1B2c3D4e5"),                      # 10 chars: lower boundary
    ("a1B2c3D4e5f6g7h", "urlId", "a1B2c3D4e5f6g7h"),            # 15 chars: upper boundary
    ("https://outline.example.com/doc/api-a1B2c3D4e5", "urlId", "a1B2c3D4e5"),
    ("/doc/api-a1B2c3D4e5?x=1#top", "urlId", "a1B2c3D4e5"),
    ("https://outline.example.com/doc/benchmark-mcp-x7Yq2Lm9Kp/edit", "urlId", "x7Yq2Lm9Kp"),
    ("title-a1B2c3D4e5", "urlId", "a1B2c3D4e5"),
    ("a1B2c3D4e", "invalid", ""),                               # 9 chars
    ("a1B2c3D4e5f6g7h8", "invalid", ""),                        # 16 chars
    ("title-short", "invalid", ""),
    ("https://example.com/other/page", "invalid", ""),
    ("", "invalid", ""),
    ("   ", "invalid", ""),
    ("invalid!", "invalid", ""),
])
def test_parse_doc_ref(raw, kind, id_):
    ref = parse_doc_ref(raw)
    assert (ref.kind, ref.id) == (kind, id_)
    if kind == "invalid":
        assert ref.error != ""


@pytest.mark.asyncio
async def test_call_real_timeout_is_reported():
    client = Client("https://outline.example.com", "test_key", timeout_ms=100)
    with patch.object(client.http, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ReadTimeout("slow")
        result = await client.call("documents.search", {})
    assert result.ok is False
    assert "timed out" in result.error
