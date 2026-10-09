import asyncio
import re
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

        except (httpx.TimeoutException, asyncio.TimeoutError):
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


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
# Measured on a live instance: 9 chars rejected, 10-15 accepted, 16 rejected.
URLID_RE = re.compile(r"^[A-Za-z0-9]{10,15}$")
REF_HINT = (
    "expected a UUID, a 10-15 character urlId, "
    "or a document URL like /doc/title-a1B2c3D4e5"
)


def parse_doc_ref(input_ref: str) -> DocRef:
    """Resolve a pasted UUID, urlId or document URL to an id documents.info accepts."""
    s = input_ref.strip() if isinstance(input_ref, str) else ""
    if not s:
        return DocRef("invalid", error=f"Empty document reference — {REF_HINT}.")
    if UUID_RE.match(s):
        return DocRef("uuid", s)

    segment = s
    idx = s.find("/doc/")
    if idx != -1:
        segment = s[idx + len("/doc/"):].split("/")[0]  # drop sub-paths such as /edit
    elif re.match(r"(?i)^https?://", s) or s.startswith("/"):
        return DocRef("invalid", error=f'"{s}" is not a document URL — {REF_HINT}.')

    segment = re.split(r"[?#]", segment)[0].rstrip("/")
    if not segment:
        return DocRef("invalid", error=f'"{s}" has no document id — {REF_HINT}.')

    candidate = segment.rsplit("-", 1)[-1]
    if URLID_RE.match(candidate):
        return DocRef("urlId", candidate)
    return DocRef("invalid", error=f'"{s}" is not a document reference — {REF_HINT}.')
