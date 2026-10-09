import os
from typing import Any, Dict

from .client import Client, parse_doc_ref
from .format import (
    abs_url,
    format_document,
    format_list,
    format_revision,
    format_search_results,
    format_title_results,
    who,
)


def _int(args: Dict[str, Any], key: str, default: int, lo: int, hi: int) -> int:
    """Read an integer argument, rejecting values outside [lo, hi]."""
    value = int(args.get(key, default))
    if not lo <= value <= hi:
        raise ValueError(f"{key} must be between {lo} and {hi}")
    return value


async def _list_call(client: Client, method: str, params: Dict[str, Any], render) -> str:
    result = await client.call(method, params)
    if not result.ok:
        return f"Error: {result.error}"
    return format_list(result.raw, render)


async def handle_search_documents(args: Dict[str, Any], client: Client) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: query parameter is required"
    try:
        params = {
            "query": query,
            "limit": _int(args, "limit", 10, 1, 50),
            "offset": _int(args, "offset", 0, 0, 10**9),
            "contextLimit": _int(args, "contextLimit", 200, 0, 1000),
        }
    except (ValueError, TypeError) as e:
        return f"Error: {e}"
    if args.get("collectionId"):
        params["collectionId"] = args["collectionId"]

    result = await client.call("documents.search", params)
    if not result.ok:
        return f"Error: {result.error}"
    return format_search_results(result.data, client.base_url)


async def handle_search_titles(args: Dict[str, Any], client: Client) -> str:
    query = args.get("query", "")
    if not query:
        return "Error: query parameter is required"
    try:
        limit = _int(args, "limit", 15, 1, 50)
    except (ValueError, TypeError) as e:
        return f"Error: {e}"

    result = await client.call("documents.search_titles", {"query": query, "limit": limit})
    if not result.ok:
        return f"Error: {result.error}"
    return format_title_results(result.data, client.base_url)


async def handle_get_document(args: Dict[str, Any], client: Client) -> str:
    id_or_url = args.get("idOrUrl", "")
    if not id_or_url:
        return "Error: idOrUrl parameter is required"
    ref = parse_doc_ref(id_or_url)
    if ref.kind == "invalid":
        return ref.error
    try:
        max_chars = _int(args, "maxChars", 40000, 0, 400000)
    except (ValueError, TypeError) as e:
        return f"Error: {e}"

    result = await client.call("documents.info", {"id": ref.id})
    if not result.ok:
        return f"Error: {result.error}"
    return format_document(result.data, client.base_url, max_chars)


async def handle_list_collections(args: Dict[str, Any], client: Client) -> str:
    try:
        params = {"limit": _int(args, "limit", 25, 1, 100), "offset": _int(args, "offset", 0, 0, 10**9)}
    except (ValueError, TypeError) as e:
        return f"Error: {e}"
    return await _list_call(client, "collections.list", params,
                            lambda c: f"{c.get('name', '')}  [{c.get('id', '')}]")


async def handle_list_documents(args: Dict[str, Any], client: Client) -> str:
    try:
        params = {"limit": _int(args, "limit", 25, 1, 100), "offset": _int(args, "offset", 0, 0, 10**9)}
    except (ValueError, TypeError) as e:
        return f"Error: {e}"
    for key in ("collectionId", "parentDocumentId"):
        if args.get(key):
            params[key] = args[key]
    return await _list_call(
        client, "documents.list", params,
        lambda d: f"{d.get('title', '')}\n   {abs_url(client.base_url, d.get('url', ''))}")


async def handle_list_revisions(args: Dict[str, Any], client: Client) -> str:
    doc_id = args.get("documentId", "")
    if not doc_id:
        return "Error: documentId parameter is required"
    try:
        params = {"documentId": doc_id, "limit": _int(args, "limit", 10, 1, 50),
                  "offset": _int(args, "offset", 0, 0, 10**9)}
    except (ValueError, TypeError) as e:
        return f"Error: {e}"
    return await _list_call(
        client, "revisions.list", params,
        lambda r: f"{r.get('createdAt', '')}  {r.get('title', '')}  [{r.get('id', '')}]")


async def handle_get_revision(args: Dict[str, Any], client: Client) -> str:
    rev_id = args.get("revisionId", "")
    if not rev_id:
        return "Error: revisionId parameter is required"
    try:
        max_chars = _int(args, "maxChars", 40000, 0, 400000)
    except (ValueError, TypeError) as e:
        return f"Error: {e}"

    result = await client.call("revisions.info", {"id": rev_id})
    if not result.ok:
        return f"Error: {result.error}"
    return format_revision(result.data, max_chars)


async def handle_list_comments(args: Dict[str, Any], client: Client) -> str:
    doc_id = args.get("documentId", "")
    if not doc_id:
        return "Error: documentId parameter is required"
    try:
        params = {"documentId": doc_id, "limit": _int(args, "limit", 25, 1, 100),
                  "offset": _int(args, "offset", 0, 0, 10**9)}
    except (ValueError, TypeError) as e:
        return f"Error: {e}"
    return await _list_call(
        client, "comments.list", params,
        lambda c: f"{c.get('createdAt', '')}  {who(c.get('createdBy'))}  [{c.get('id', '')}]")


async def _write_blocked(client: Client, tool: str, document_id: str = "") -> str:
    """Optional OUTLINE_WRITE_DOC_ID restriction: when set, writes are confined
    to update_document on that single document. The allowed id and the target may
    be written differently (UUID vs urlId); when they are, Outline is asked to
    resolve the target so both names compare equal."""
    allowed = os.environ.get("OUTLINE_WRITE_DOC_ID", "").strip()
    if not allowed:
        return ""
    if tool != "update_document":
        return (f"Error: writes are restricted to one document (OUTLINE_WRITE_DOC_ID); "
                f"{tool} is not allowed.")
    want, got = parse_doc_ref(allowed), parse_doc_ref(document_id)
    valid = "invalid" not in (want.kind, got.kind)
    ok = valid and want.id == got.id
    if valid and not ok and want.kind != got.kind:
        info = await client.call("documents.info", {"id": got.id})
        d = info.data if info.ok and isinstance(info.data, dict) else {}
        ok = want.id in (d.get("id"), d.get("urlId"))
    return "" if ok else "Error: this server may only update the document named by OUTLINE_WRITE_DOC_ID"


async def _with_document(args: Dict[str, Any], client: Client, tool: str, run) -> str:
    """Resolve the document argument, apply the write guard, then run the call."""
    doc_id = args.get("documentId", "")
    if not doc_id:
        return "Error: documentId parameter is required"
    ref = parse_doc_ref(doc_id)
    if ref.kind == "invalid":
        return ref.error
    blocked = await _write_blocked(client, tool, doc_id)
    if blocked:
        return blocked
    return await run(ref.id)


def _describe_doc(data: Any, base_url: str) -> str:
    d = data if isinstance(data, dict) else {}
    return f'"{d.get("title", "")}" ({len(d.get("text", ""))} characters)\n{abs_url(base_url, d.get("url", ""))}'


async def _write_call(client: Client, method: str, params: Dict[str, Any], done) -> str:
    result = await client.call(method, params)
    if not result.ok:
        return f"Error: {result.error}"
    return done(result.data)


async def handle_create_document(args: Dict[str, Any], client: Client) -> str:
    blocked = await _write_blocked(client, "create_document")
    if blocked:
        return blocked
    if not args.get("title") or not args.get("collectionId"):
        return "Error: title and collectionId parameters are required"
    params = {"title": args["title"], "text": args.get("text", ""),
              "collectionId": args["collectionId"], "publish": bool(args.get("publish", True))}
    if args.get("parentDocumentId"):
        params["parentDocumentId"] = args["parentDocumentId"]
    return await _write_call(client, "documents.create", params,
                             lambda d: "Created " + _describe_doc(d, client.base_url))


async def handle_update_document(args: Dict[str, Any], client: Client) -> str:
    async def run(doc_id: str) -> str:
        params = {"id": doc_id, "append": bool(args.get("append", True))}
        for key in ("text", "title"):
            if isinstance(args.get(key), str):
                params[key] = args[key]
        return await _write_call(client, "documents.update", params,
                                 lambda d: "Updated " + _describe_doc(d, client.base_url))
    return await _with_document(args, client, "update_document", run)


async def handle_move_document(args: Dict[str, Any], client: Client) -> str:
    async def run(doc_id: str) -> str:
        params = {"id": doc_id}
        for key in ("collectionId", "parentDocumentId"):
            if args.get(key):
                params[key] = args[key]
        return await _write_call(client, "documents.move", params, lambda _d: f"Moved document {doc_id}")
    return await _with_document(args, client, "move_document", run)


async def handle_archive_document(args: Dict[str, Any], client: Client) -> str:
    async def run(doc_id: str) -> str:
        return await _write_call(client, "documents.archive", {"id": doc_id},
                                 lambda _d: f"Archived document {doc_id}")
    return await _with_document(args, client, "archive_document", run)


async def handle_delete_document(args: Dict[str, Any], client: Client) -> str:
    async def run(doc_id: str) -> str:
        return await _write_call(client, "documents.delete", {"id": doc_id},
                                 lambda _d: f"Moved document {doc_id} to the trash")
    return await _with_document(args, client, "delete_document", run)


def _obj(required, props):
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema


def _str(desc):
    return {"type": "string", "description": desc}


def _int_schema(desc, lo, hi=None):
    s = {"type": "integer", "description": desc, "minimum": lo}
    if hi is not None:
        s["maximum"] = hi
    return s


_LIMIT50 = _int_schema("Max results", 1, 50)
_LIMIT100 = _int_schema("Max results", 1, 100)
_OFFSET = _int_schema("Results to skip", 0)
_MAX_CHARS = _int_schema("Maximum characters of body to return", 0, 400000)

TOOLS = [
    {
        "name": "search_documents",
        "description": (
            "Full-text search across your Outline wiki. Returns each hit as "
            "title, absolute URL and a matching snippet — NOT the full document body. "
            "Use this when you do not yet know which document you need. Once you have "
            "a URL or id, call get_document to read the body."
        ),
        "schema": _obj(["query"], {
            "query": _str("Search terms"),
            "collectionId": _str("Restrict the search to one collection"),
            "limit": _LIMIT50,
            "offset": _OFFSET,
            "contextLimit": _int_schema("Characters of surrounding context per hit", 0, 1000),
        }),
        "handler": handle_search_documents,
    },
    {
        "name": "search_document_titles",
        "description": (
            "Search Outline document TITLES only. Cheaper and more precise than "
            "search_documents when you already know roughly what the page is called "
            "and only need to locate it. Returns titles and absolute URLs, no snippets."
        ),
        "schema": _obj(["query"], {"query": _str("Words expected in the title"), "limit": _LIMIT50}),
        "handler": handle_search_titles,
    },
    {
        "name": "get_document",
        "description": (
            "Read one Outline document as markdown. Accepts a full document URL "
            "(https://host/doc/some-title-a1B2c3D4e5), a bare urlId, or a UUID. Long "
            "documents are truncated at maxChars with a marker stating the true total "
            "length — raise maxChars and call again if you need the rest."
        ),
        "schema": _obj(["idOrUrl"], {"idOrUrl": _str("Document URL, urlId, or UUID"), "maxChars": _MAX_CHARS}),
        "handler": handle_get_document,
    },
    {
        "name": "list_collections",
        "description": (
            "List the collections (top-level spaces) in the Outline wiki. Use this "
            "first when you need to scope a search or browse, since collectionId is "
            "what search_documents and list_documents filter on."
        ),
        "schema": _obj(None, {"limit": _LIMIT100, "offset": _OFFSET}),
        "handler": handle_list_collections,
    },
    {
        "name": "list_documents",
        "description": (
            "Browse Outline documents without searching. Pass collectionId to list a "
            "collection, or parentDocumentId to walk into one document's children. "
            "Returns titles and absolute URLs only — call get_document to read one."
        ),
        "schema": _obj(None, {
            "collectionId": _str("List documents in this collection"),
            "parentDocumentId": _str("List children of this document"),
            "limit": _LIMIT100,
            "offset": _OFFSET,
        }),
        "handler": handle_list_documents,
    },
    {
        "name": "list_revisions",
        "description": (
            "List the saved revisions of one Outline document, newest first. Use this "
            "to see how a spec changed over time; pair it with get_revision to read a "
            "specific earlier version."
        ),
        "schema": _obj(["documentId"], {"documentId": _str("UUID of the document"),
                                        "limit": _LIMIT50, "offset": _OFFSET}),
        "handler": handle_list_revisions,
    },
    {
        "name": "get_revision",
        "description": (
            "Read one earlier version of an Outline document as markdown. Get the "
            "revision id from list_revisions first. Use this to diff what a spec said "
            "before against what it says now."
        ),
        "schema": _obj(["revisionId"], {"revisionId": _str("Revision id from list_revisions"),
                                        "maxChars": _MAX_CHARS}),
        "handler": handle_get_revision,
    },
    {
        "name": "list_comments",
        "description": (
            "List review comments left on one Outline document. Use this when a spec "
            "has open questions or reviewer pushback that is not reflected in the body "
            "text itself."
        ),
        "schema": _obj(["documentId"], {"documentId": _str("UUID of the document"),
                                        "limit": _LIMIT100, "offset": _OFFSET}),
        "handler": handle_list_comments,
    },
    {
        "name": "create_document",
        "description": (
            "Create a new Outline document. Pass collectionId (and optionally "
            "parentDocumentId to nest it). Published immediately unless publish=false."
        ),
        "schema": _obj(["title", "collectionId"], {
            "title": _str("Document title"),
            "text": _str("Markdown body"),
            "collectionId": _str("Collection to create the document in"),
            "parentDocumentId": _str("Nest under this document"),
            "publish": {"type": "boolean", "description": "Publish immediately (default) or leave as draft"},
        }),
        "handler": handle_create_document,
    },
    {
        "name": "update_document",
        "description": (
            "Edit an Outline document's body and/or title. Appends text by default; "
            "pass append=false to replace the body. Accepts a URL, urlId or UUID."
        ),
        "schema": _obj(["documentId"], {
            "documentId": _str("Document URL, urlId, or UUID"),
            "text": _str("Markdown to write"),
            "title": _str("New title"),
            "append": {"type": "boolean", "description": "Append (default) or replace the body"},
        }),
        "handler": handle_update_document,
    },
    {
        "name": "move_document",
        "description": "Move an Outline document to another collection and/or under another parent document.",
        "schema": _obj(["documentId"], {
            "documentId": _str("Document URL, urlId, or UUID"),
            "collectionId": _str("Destination collection"),
            "parentDocumentId": _str("Destination parent document"),
        }),
        "handler": handle_move_document,
    },
    {
        "name": "archive_document",
        "description": "Archive an Outline document (recoverable from the archive).",
        "schema": _obj(["documentId"], {"documentId": _str("Document URL, urlId, or UUID")}),
        "handler": handle_archive_document,
    },
    {
        "name": "delete_document",
        "description": (
            "Delete an Outline document. It goes to the trash and can be restored; "
            "this tool never deletes permanently."
        ),
        "schema": _obj(["documentId"], {"documentId": _str("Document URL, urlId, or UUID")}),
        "handler": handle_delete_document,
    },
]
