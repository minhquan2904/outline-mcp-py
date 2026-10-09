from typing import Dict, Any
from .client import Client, parse_doc_ref
from .format import *


async def handle_search_documents(args: Dict[str, Any], client: Client) -> str:
    """Search full-text across wiki"""
    query = args.get("query", "")
    if not query:
        return "Error: query parameter is required"

    try:
        limit = int(args.get("limit", 10))
        if not (1 <= limit <= 50):
            return "Error: limit must be between 1 and 50"

        offset = int(args.get("offset", 0))
        if offset < 0:
            return "Error: offset must be >= 0"

        context_limit = int(args.get("contextLimit", 200))
        if not (0 <= context_limit <= 1000):
            return "Error: contextLimit must be between 0 and 1000"
    except (ValueError, TypeError):
        return "Error: invalid parameter type"

    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "contextLimit": context_limit,
    }
    if "collectionId" in args and args["collectionId"]:
        params["collectionId"] = args["collectionId"]

    result = await client.call("documents.search", params)
    if not result.ok:
        return f"Error: {result.error}"

    return format_search_results(result.data or {}, client.base_url)


async def handle_search_titles(args: Dict[str, Any], client: Client) -> str:
    """Search document titles only"""
    query = args.get("query", "")
    if not query:
        return "Error: query parameter is required"

    try:
        limit = int(args.get("limit", 15))
        if not (1 <= limit <= 50):
            return "Error: limit must be between 1 and 50"
    except (ValueError, TypeError):
        return "Error: invalid parameter type"

    params = {"query": query, "limit": limit}

    result = await client.call("documents.search_titles", params)
    if not result.ok:
        return f"Error: {result.error}"

    return format_title_results(result.data or {}, client.base_url)


async def handle_get_document(args: Dict[str, Any], client: Client) -> str:
    """Read one document as markdown"""
    id_or_url = args.get("idOrUrl", "")
    if not id_or_url:
        return "Error: idOrUrl parameter is required"

    ref = parse_doc_ref(id_or_url)
    if ref.kind == "invalid":
        return f"Error: {ref.error}"

    try:
        max_chars = int(args.get("maxChars", 40000))
        if not (0 <= max_chars <= 400000):
            return "Error: maxChars must be between 0 and 400000"
    except (ValueError, TypeError):
        return "Error: invalid parameter type"

    result = await client.call("documents.info", {"id": ref.id})
    if not result.ok:
        return f"Error: {result.error}"

    return format_document(result.data or {}, client.base_url, max_chars)


async def handle_list_collections(args: Dict[str, Any], client: Client) -> str:
    """List wiki collections (spaces)"""
    try:
        limit = int(args.get("limit", 25))
        if not (1 <= limit <= 100):
            return "Error: limit must be between 1 and 100"

        offset = int(args.get("offset", 0))
        if offset < 0:
            return "Error: offset must be >= 0"
    except (ValueError, TypeError):
        return "Error: invalid parameter type"

    result = await client.call("collections.list", {"limit": limit, "offset": offset})
    if not result.ok:
        return f"Error: {result.error}"

    data = result.data or {}
    collections = data.get("results", [])

    return format_list(
        collections,
        lambda c: f"{c.get('name', '')}  [{c.get('id', '')}]"
    )


async def handle_list_documents(args: Dict[str, Any], client: Client) -> str:
    """Browse documents without searching"""
    try:
        limit = int(args.get("limit", 25))
        if not (1 <= limit <= 100):
            return "Error: limit must be between 1 and 100"

        offset = int(args.get("offset", 0))
        if offset < 0:
            return "Error: offset must be >= 0"
    except (ValueError, TypeError):
        return "Error: invalid parameter type"

    params = {"limit": limit, "offset": offset}
    if "collectionId" in args and args["collectionId"]:
        params["collectionId"] = args["collectionId"]
    if "parentDocumentId" in args and args["parentDocumentId"]:
        params["parentDocumentId"] = args["parentDocumentId"]

    result = await client.call("documents.list", params)
    if not result.ok:
        return f"Error: {result.error}"

    data = result.data or {}
    documents = data.get("results", [])

    return format_list(
        documents,
        lambda d: f"{d.get('title', '')}\n   {_abs_url(client.base_url, d.get('url', ''))}"
    )


async def handle_list_revisions(args: Dict[str, Any], client: Client) -> str:
    """List document revisions"""
    doc_id = args.get("documentId", "")
    if not doc_id:
        return "Error: documentId parameter is required"

    try:
        limit = int(args.get("limit", 10))
        if not (1 <= limit <= 50):
            return "Error: limit must be between 1 and 50"

        offset = int(args.get("offset", 0))
        if offset < 0:
            return "Error: offset must be >= 0"
    except (ValueError, TypeError):
        return "Error: invalid parameter type"

    result = await client.call(
        "revisions.list",
        {"documentId": doc_id, "limit": limit, "offset": offset}
    )
    if not result.ok:
        return f"Error: {result.error}"

    data = result.data or {}
    revisions = data.get("results", [])

    return format_list(
        revisions,
        lambda r: f"{r.get('createdAt', '')}  {r.get('title', '')}  [{r.get('id', '')}]"
    )


async def handle_get_revision(args: Dict[str, Any], client: Client) -> str:
    """Read an older version of a document"""
    rev_id = args.get("revisionId", "")
    if not rev_id:
        return "Error: revisionId parameter is required"

    try:
        max_chars = int(args.get("maxChars", 40000))
        if not (0 <= max_chars <= 400000):
            return "Error: maxChars must be between 0 and 400000"
    except (ValueError, TypeError):
        return "Error: invalid parameter type"

    result = await client.call("revisions.info", {"id": rev_id})
    if not result.ok:
        return f"Error: {result.error}"

    return format_revision(result.data or {}, max_chars)


TOOLS = [
    {
        "name": "search_documents",
        "description": (
            "Full-text search across your Outline wiki. Returns each hit as "
            "title, absolute URL and a matching snippet — NOT the full document body. "
            "Use this when you do not yet know which document you need."
        ),
        "handler": handle_search_documents,
    },
    {
        "name": "search_document_titles",
        "description": (
            "Search Outline document TITLES only. Cheaper and more precise than "
            "search_documents when you already know roughly what the page is called."
        ),
        "handler": handle_search_titles,
    },
    {
        "name": "get_document",
        "description": (
            "Read one Outline document as markdown. Accepts a full document URL, "
            "a bare urlId, or a UUID. Long documents are truncated at maxChars."
        ),
        "handler": handle_get_document,
    },
    {
        "name": "list_collections",
        "description": (
            "List the collections (top-level spaces) in the Outline wiki."
        ),
        "handler": handle_list_collections,
    },
    {
        "name": "list_documents",
        "description": (
            "Browse Outline documents without searching. Pass collectionId or "
            "parentDocumentId to filter."
        ),
        "handler": handle_list_documents,
    },
    {
        "name": "list_revisions",
        "description": (
            "List the saved revisions of one Outline document, newest first."
        ),
        "handler": handle_list_revisions,
    },
    {
        "name": "get_revision",
        "description": (
            "Read one earlier version of an Outline document as markdown."
        ),
        "handler": handle_get_revision,
    },
]


def _abs_url(base_url: str, rel_path: str) -> str:
    """Resolve relative URL"""
    from urllib.parse import urljoin
    if rel_path.startswith(("http://", "https://")):
        return rel_path
    return urljoin(base_url.rstrip("/") + "/", rel_path.lstrip("/"))
