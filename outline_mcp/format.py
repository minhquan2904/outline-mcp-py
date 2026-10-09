"""Rendering helpers. Output mirrors the JavaScript reference implementation
(outline-mcp/format.js) so all three servers answer identically."""
import re
from typing import Any, Callable, Dict, Tuple

NO_RESULTS = "No results."


def _s(value: Any) -> str:
    return "" if value is None else str(value)


def _or(value: Any, default: str) -> str:
    return _s(value) or default


def abs_url(base_url: str, path: str) -> str:
    """Turn Outline's relative document paths into absolute links."""
    if not path:
        return ""
    if re.match(r"(?i)^https?://", path):
        return path
    base = (base_url or "").rstrip("/")
    return base + (path if path.startswith("/") else "/" + path)


def truncate(text: Any, max_chars: int) -> Tuple[str, int]:
    """Cut the body at max_chars characters and report the original length."""
    t = text if isinstance(text, str) else ""
    total = len(t)
    if total <= max_chars:
        return t, total
    marker = (
        f"\n\n[... truncated — showing {max_chars} of {total} characters. "
        "Call again with a larger maxChars to read the rest.]"
    )
    return t[:max_chars] + marker, total


def _doc_line(doc: Dict[str, Any], base_url: str, index: int) -> str:
    return f"{index + 1}. {_or(doc.get('title'), '(untitled)')}\n   {abs_url(base_url, _s(doc.get('url')))}"


def format_search_results(hits: Any, base_url: str) -> str:
    """documents.search hits are wrapped as {context, document, ranking}."""
    if not isinstance(hits, list) or not hits:
        return NO_RESULTS
    parts = []
    for i, hit in enumerate(hits):
        line = _doc_line(hit.get("document") or {}, base_url, i)
        ctx = _s(hit.get("context")).strip()
        parts.append(f"{line}\n   {ctx}" if ctx else line)
    return "\n\n".join(parts)


def format_title_results(docs: Any, base_url: str) -> str:
    """documents.search_titles returns bare document objects."""
    if not isinstance(docs, list) or not docs:
        return NO_RESULTS
    return "\n".join(_doc_line(d or {}, base_url, i) for i, d in enumerate(docs))


def who(person: Any, fallback: str = "") -> str:
    name = person.get("name") if isinstance(person, dict) else None
    return name or fallback or "unknown"


def format_document(doc: Any, base_url: str, max_chars: int) -> str:
    d = doc if isinstance(doc, dict) else {}
    body, _ = truncate(d.get("text"), max_chars)
    header = "\n".join([
        f"# {_or(d.get('title'), '(untitled)')}",
        f"id: {_s(d.get('id'))} · urlId: {_s(d.get('urlId'))} · collection: {_s(d.get('collectionId'))}",
        f"url: {abs_url(base_url, _s(d.get('url')))}",
        f"updated: {_or(d.get('updatedAt'), 'unknown')} by {who(d.get('updatedBy'))}",
    ])
    return f"{header}\n---\n{body}"


def format_revision(rev: Any, max_chars: int) -> str:
    r = rev if isinstance(rev, dict) else {}
    body, _ = truncate(r.get("text"), max_chars)
    header = "\n".join([
        f"# {_or(r.get('title'), '(untitled)')} (revision {_s(r.get('id'))})",
        f"document: {_s(r.get('documentId'))}",
        f"created: {_or(r.get('createdAt'), 'unknown')} by {who(r.get('createdBy'), _s(r.get('name')))}",
    ])
    return f"{header}\n---\n{body}"


def format_list(payload: Any, render: Callable[[Dict[str, Any]], str]) -> str:
    """Generic list renderer that keeps the pagination cursor visible."""
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list) or not data:
        return NO_RESULTS
    lines = [f"{i + 1}. {render(item or {})}" for i, item in enumerate(data)]
    p = payload.get("pagination")
    if p:
        parts = [f"limit={_s(p.get('limit'))}", f"offset={_s(p.get('offset'))}"]
        if "total" in p:
            parts.append(f"total={_s(p['total'])}")
        lines += ["", "[" + " · ".join(parts) + "]"]
    return "\n".join(lines)
