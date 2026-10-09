import asyncio
import httpx
from typing import Dict, Any, Optional
import json
from .types import Result, DocRef

DEFAULT_TIMEOUT_MS = 30000
MAX_RETRY_DELAY_MS = 10000
FALLBACK_RETRY_MS = 1000


class Client:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_ms = timeout_ms
        self.http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_ms / 1000),
            follow_redirects=False,
        )

    async def call(self, method: str, params: Dict[str, Any]) -> Result:
        """Call Outline API via POST /api/{method}"""
        if not self.base_url:
            return Result(
                False,
                error="$OUTLINE_API_URL is not set, so there is no Outline instance to call.",
            )
        if not self.api_key:
            return Result(
                False,
                error="$OUTLINE_API_KEY is not set. Add it to environment or config.",
            )

        url = f"{self.base_url}/api/{method}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = await self.http.post(url, json=params, headers=headers)

            # Retry on 429
            if response.status_code == 429:
                retry_delay = self._retry_delay_ms(response)
                await asyncio.sleep(retry_delay / 1000)
                response = await self.http.post(url, json=params, headers=headers)

            if response.status_code != 200:
                error_msg = self._describe_failure(method, response)
                return Result(False, error=self._redact(error_msg))

            data = response.json()
            return Result(True, data=data.get("data"), raw=data)

        except asyncio.TimeoutError:
            msg = f"Request to Outline timed out after {self.timeout_ms}ms on {method}"
            return Result(False, error=self._redact(msg))
        except Exception as e:
            msg = f"Could not reach Outline for {method}: {str(e)}"
            return Result(False, error=self._redact(msg))

    def _retry_delay_ms(self, response: httpx.Response) -> int:
        """Parse Retry-After header"""
        raw = response.headers.get("retry-after", "")
        try:
            seconds = int(raw)
            if seconds <= 0:
                return FALLBACK_RETRY_MS
            ms = seconds * 1000
            return min(ms, MAX_RETRY_DELAY_MS)
        except ValueError:
            return FALLBACK_RETRY_MS

    def _describe_failure(self, method: str, response: httpx.Response) -> str:
        """Map HTTP status to user-friendly error message"""
        status = response.status_code
        try:
            body = response.json()
            upstream = body.get("error", "")
        except:
            upstream = ""

        if status == 401:
            return (
                f"Outline rejected the credentials (401: {upstream}). "
                "Check that $OUTLINE_API_KEY holds a valid API key."
            )
        elif status == 403:
            return (
                f"Outline refused the request (403: {upstream}). "
                f"The key is valid but lacks permission for {method}."
            )
        elif status == 404:
            return (
                f"Not found (404) for {method}: {upstream}. "
                "The id or slug is missing."
            )
        elif status == 429:
            return (
                "Outline rate limit hit (429). "
                "Wait a moment and retry."
            )
        else:
            return f"Outline returned {status} for {method}: {upstream}"

    def _redact(self, text: str) -> str:
        """Redact API key from error messages"""
        if not self.api_key:
            return text
        return text.replace(self.api_key, "ol_api_***")


def parse_doc_ref(id_or_url: str) -> DocRef:
    """Parse document reference (URL, UUID, or bare ID)"""
    id_or_url = id_or_url.strip()

    # UUID format: 550e8400-e29b-41d4-a716-446655440000
    if len(id_or_url) == 36 and id_or_url.count("-") == 4:
        return DocRef("uuid", id_or_url)

    # URL format: https://host/doc/title-a1B2c3D4e5
    if id_or_url.startswith(("http://", "https://")):
        parts = id_or_url.split("/")
        if len(parts) > 0:
            last = parts[-1]
            if "-" in last:
                url_id = last.split("-")[-1]
                if len(url_id) >= 7:
                    return DocRef("url", url_id)
        return DocRef("invalid", error="URL format: expected /doc/title-urlId")

    # Bare ID (alphanumeric, at least 7 chars)
    if len(id_or_url) >= 7 and _is_alphanumeric(id_or_url):
        return DocRef("id", id_or_url)

    return DocRef("invalid", error="Invalid document reference format")


def _is_alphanumeric(s: str) -> bool:
    """Check if string is alphanumeric (plus - and _)"""
    for c in s:
        if not (c.isalnum() or c in "-_"):
            return False
    return True
