from outline_mcp.format import (
    abs_url, format_document, format_list, format_search_results,
    format_title_results, truncate,
)


def test_truncate():
    assert truncate("hello", 5) == ("hello", 5)
    text, total = truncate("hello!", 5)
    assert total == 6
    assert text.startswith("hello\n\n[... truncated — showing 5 of 6 characters.")
    assert truncate("", 0) == ("", 0)
    assert truncate("tiếng Việt", 5)[0].startswith("tiếng")


def test_abs_url():
    assert abs_url("https://o.example.com", "/doc/x-abc") == "https://o.example.com/doc/x-abc"
    assert abs_url("https://o.example.com/", "/doc/x-abc") == "https://o.example.com/doc/x-abc"
    assert abs_url("https://o.example.com", "https://other/doc") == "https://other/doc"
    assert abs_url("", "/doc/x") == "/doc/x"
    assert abs_url("https://o.example.com", "") == ""


def test_format_search_results():
    hits = [
        {"context": " snippet one ", "document": {"title": "First", "url": "/doc/first-abc"}},
        {"document": {"url": "/doc/second-abc"}},
    ]
    assert format_search_results(hits, "https://o.example.com") == (
        "1. First\n   https://o.example.com/doc/first-abc\n   snippet one\n\n"
        "2. (untitled)\n   https://o.example.com/doc/second-abc"
    )
    assert format_search_results([], "") == "No results."


def test_format_title_results():
    docs = [{"title": "A", "url": "/doc/a"}, {"title": "B", "url": "/doc/b"}]
    assert format_title_results(docs, "https://h") == "1. A\n   https://h/doc/a\n2. B\n   https://h/doc/b"


def test_format_document():
    doc = {"title": "Spec", "id": "uuid-1", "urlId": "abc1234567", "collectionId": "col-1",
           "url": "/doc/spec-abc1234567", "updatedAt": "2026-01-02T03:04:05Z",
           "updatedBy": {"name": "Quan"}, "text": "body text"}
    assert format_document(doc, "https://h", 100) == (
        "# Spec\nid: uuid-1 · urlId: abc1234567 · collection: col-1\n"
        "url: https://h/doc/spec-abc1234567\nupdated: 2026-01-02T03:04:05Z by Quan\n---\nbody text"
    )
    assert "by unknown" in format_document({"text": "x"}, "", 10)


def test_format_list():
    payload = {"data": [{"name": "Eng", "id": "c1"}, {"name": "Ops", "id": "c2"}],
               "pagination": {"limit": 25, "offset": 0, "total": 2}}
    out = format_list(payload, lambda c: f"{c['name']}  [{c['id']}]")
    assert out == "1. Eng  [c1]\n2. Ops  [c2]\n\n[limit=25 · offset=0 · total=2]"
    assert format_list({}, None) == "No results."
