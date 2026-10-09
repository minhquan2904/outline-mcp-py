from typing import Any


class Result:
    """Outcome of one Outline API call."""

    def __init__(self, ok: bool, data: Any = None, raw: Any = None, error: str = ""):
        self.ok = ok
        self.data = data
        self.raw = raw if raw is not None else {}
        self.error = error


class DocRef:
    """Parsed document reference."""

    def __init__(self, kind: str, id: str = "", error: str = ""):
        self.kind = kind  # "uuid", "urlId", "invalid"
        self.id = id
        self.error = error
