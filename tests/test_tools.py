import pytest
from unittest.mock import AsyncMock, MagicMock

from outline_mcp.client import Client
from outline_mcp.tools import (
    TOOLS, handle_archive_document, handle_create_document, handle_delete_document,
    handle_get_document, handle_move_document, handle_update_document,
)
from outline_mcp.types import Result

DOC = "3f9a2c10-1b2c-4d5e-8f90-abcdef123456"
OTHER = "11111111-2222-3333-4444-555555555555"


def test_tool_surface_matches_the_reference_server():
    assert [t["name"] for t in TOOLS] == [
        "search_documents", "search_document_titles", "get_document", "list_collections",
        "list_documents", "list_revisions", "get_revision", "list_comments", "create_document",
        "update_document", "move_document", "archive_document", "delete_document",
    ]
    assert all(t["schema"]["type"] == "object" for t in TOOLS)


@pytest.mark.asyncio
async def test_get_document_accepts_an_edit_url():
    client = MagicMock(base_url="https://h")
    client.call = AsyncMock(return_value=Result(True, data={"title": "T", "text": "body"}))
    out = await handle_get_document({"idOrUrl": "https://h/doc/benchmark-mcp-x7Yq2Lm9Kp/edit"}, client)
    client.call.assert_awaited_once_with("documents.info", {"id": "x7Yq2Lm9Kp"})
    assert out.startswith("# T")


def _client(data=None):
    client = MagicMock(base_url="https://h")
    client.call = AsyncMock(return_value=Result(True, data=data or {"title": "T", "text": "abc", "url": "/doc/t-x"}))
    return client


@pytest.mark.asyncio
async def test_write_tools_have_full_rights_without_a_restriction(monkeypatch):
    monkeypatch.delenv("OUTLINE_WRITE_DOC_ID", raising=False)
    client = _client()
    await handle_create_document({"title": "T", "text": "abc", "collectionId": OTHER}, client)
    await handle_update_document({"documentId": OTHER, "text": "abc"}, client)
    await handle_move_document({"documentId": OTHER, "collectionId": DOC}, client)
    await handle_archive_document({"documentId": OTHER}, client)
    await handle_delete_document({"documentId": OTHER}, client)
    assert [c.args[0] for c in client.call.await_args_list] == [
        "documents.create", "documents.update", "documents.move", "documents.archive", "documents.delete"]
    assert client.call.await_args_list[1].args[1] == {"id": OTHER, "append": True, "text": "abc"}


@pytest.mark.asyncio
async def test_update_accepts_a_pasted_edit_url(monkeypatch):
    monkeypatch.delenv("OUTLINE_WRITE_DOC_ID", raising=False)
    client = _client()
    await handle_update_document({"documentId": "https://h/doc/benchmark-mcp-x7Yq2Lm9Kp/edit", "text": "x"}, client)
    assert client.call.await_args.args[1]["id"] == "x7Yq2Lm9Kp"


@pytest.mark.asyncio
async def test_restriction_confines_writes_to_one_document(monkeypatch):
    monkeypatch.setenv("OUTLINE_WRITE_DOC_ID", DOC)
    client = _client()
    assert "may only update" in await handle_update_document({"documentId": OTHER, "text": "x"}, client)
    assert "writes are restricted" in await handle_delete_document({"documentId": DOC}, client)
    assert "writes are restricted" in await handle_create_document({"title": "t", "collectionId": DOC}, client)
    client.call.assert_not_awaited()
    await handle_update_document({"documentId": DOC, "text": "x"}, client)
    client.call.assert_awaited_once()


@pytest.mark.asyncio
async def test_restriction_resolves_uuid_and_urlid_to_the_same_document(monkeypatch):
    monkeypatch.setenv("OUTLINE_WRITE_DOC_ID", DOC)
    client = MagicMock(base_url="https://h")
    client.call = AsyncMock(side_effect=[
        Result(True, data={"id": DOC, "urlId": "x7Yq2Lm9Kp"}),
        Result(True, data={"title": "T", "text": "x", "url": "/doc/t-x"}),
    ])
    out = await handle_update_document({"documentId": "https://h/doc/b-x7Yq2Lm9Kp/edit", "text": "x"}, client)
    assert out.startswith("Updated")
    assert [c.args[0] for c in client.call.await_args_list] == ["documents.info", "documents.update"]


@pytest.mark.asyncio
async def test_restriction_refuses_a_urlid_of_another_document(monkeypatch):
    monkeypatch.setenv("OUTLINE_WRITE_DOC_ID", DOC)
    client = MagicMock(base_url="https://h")
    client.call = AsyncMock(return_value=Result(True, data={"id": OTHER, "urlId": "zzzzzzzzzz"}))
    out = await handle_update_document({"documentId": "x7Yq2Lm9Kp", "text": "x"}, client)
    assert "may only update" in out
    client.call.assert_awaited_once()
