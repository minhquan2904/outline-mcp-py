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


def test_parse_doc_ref_url():
    ref = parse_doc_ref("https://outline.example.com/doc/api-design-a1B2c3D4e5")
    assert ref.kind == "url"
    assert ref.id == "a1B2c3D4e5"


def test_parse_doc_ref_uuid():
    ref = parse_doc_ref("550e8400-e29b-41d4-a716-446655440000")
    assert ref.kind == "uuid"
    assert ref.id == "550e8400-e29b-41d4-a716-446655440000"


def test_parse_doc_ref_bare_id():
    ref = parse_doc_ref("api_design_123456")
    assert ref.kind == "id"
    assert ref.id == "api_design_123456"


def test_parse_doc_ref_invalid():
    ref = parse_doc_ref("invalid!")
    assert ref.kind == "invalid"
    assert ref.error != ""
