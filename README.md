# outline-mcp-py

Read-only MCP server for Outline wiki, written in Python using the official MCP SDK.

## Setup

```bash
pip install -e ".[dev]"
```

## Test

```bash
make test
# or
pytest -v tests/
```

## Run

```bash
export OUTLINE_API_URL=https://outline.example.com
export OUTLINE_API_KEY=your_api_key
python -m outline_mcp.main
```

## Tools

- `search_documents` — Full-text search
- `search_document_titles` — Search titles only
- `get_document` — Read one document
- `list_collections` — List wiki spaces
- `list_documents` — Browse documents
- `list_revisions` — List document versions
- `get_revision` — Read an older version

## Architecture

- `types.py` — Pydantic models for Outline API
- `client.py` — Async HTTP RPC client (httpx)
- `format.py` — Output rendering
- `tools.py` — MCP tool handlers
- `main.py` — Server entry point

## Implementation Notes

- 3 dependencies: mcp-sdk, pydantic, httpx
- Async/await for concurrency
- Manual parameter validation
- API key redaction in errors
- Timeout: 30s per request
- Retry on 429 (rate limit): max 10s wait

## TODO

- [ ] Integration tests
- [ ] Handle pagination
- [ ] Add list_comments tool
