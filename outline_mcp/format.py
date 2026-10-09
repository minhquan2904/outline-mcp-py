from typing import Dict, Any, List, Callable
from urllib.parse import urljoin


def format_search_results(data: Dict[str, Any], base_url: str) -> str:
    """Format search results: Title\nURL\nSnippet\n\n..."""
    results = data.get("results", []) if isinstance(data, dict) else []
    lines = []

    for result in results:
        title = result.get("title", "")
        url = result.get("url", "")
        snippet = result.get("snippet", "")

        abs_url = _abs_url(base_url, url)
        lines.append(f"{title}\n{abs_url}\n{snippet}\n")

    return "\n".join(lines)


def format_document(data: Dict[str, Any], base_url: str, max_chars: int) -> str:
    """Format document: # Title\n\nMarkdown body\n\n_(truncated...)_"""
    title = data.get("title", "") if isinstance(data, dict) else ""
    text = data.get("text", "") if isinstance(data, dict) else ""

    truncated = False
    if max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    output = f"# {title}\n\n{text}"

    if truncated:
        true_length = len(data.get("text", ""))
        output += f"\n\n_(truncated; true length: {true_length} characters)_"

    return output


def format_list(items: List[Dict], item_fmt: Callable) -> str:
    """Format list: items separated by newlines"""
    return "\n".join([item_fmt(item) for item in items])


def format_title_results(data: Dict[str, Any], base_url: str) -> str:
    """Format title search results (same as search_results)"""
    return format_search_results(data, base_url)


def format_revision(data: Dict[str, Any], max_chars: int) -> str:
    """Format revision: # Title (Revision)\n\nMarkdown"""
    title = data.get("title", "") if isinstance(data, dict) else ""
    text = data.get("text", "") if isinstance(data, dict) else ""

    truncated = False
    if max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    output = f"# {title} (Revision)\n\n{text}"

    if truncated:
        true_length = len(data.get("text", ""))
        output += f"\n\n_(truncated; true length: {true_length} characters)_"

    return output


def _abs_url(base_url: str, rel_path: str) -> str:
    """Resolve relative URL"""
    if rel_path.startswith(("http://", "https://")):
        return rel_path
    return urljoin(base_url.rstrip("/") + "/", rel_path.lstrip("/"))
