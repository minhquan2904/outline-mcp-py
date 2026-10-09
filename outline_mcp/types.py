from pydantic import BaseModel, Field
from typing import Optional, List, Any


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchData(BaseModel):
    results: List[SearchResult]
    pagination: dict = Field(default_factory=dict)


class Document(BaseModel):
    id: str
    title: str
    url: str
    text: str


class Collection(BaseModel):
    id: str
    name: str


class CollectionsData(BaseModel):
    results: List[Collection]
    pagination: dict = Field(default_factory=dict)


class Revision(BaseModel):
    id: str
    title: str
    createdAt: str


class RevisionsData(BaseModel):
    results: List[Revision]
    pagination: dict = Field(default_factory=dict)


class Comment(BaseModel):
    id: str
    createdAt: str
    createdBy: dict = Field(default_factory=dict)


class CommentsData(BaseModel):
    results: List[Comment]
    pagination: dict = Field(default_factory=dict)


class APIResponse(BaseModel):
    data: Optional[Any] = None
    error: Optional[str] = None


class Result:
    """Internal result wrapper"""
    def __init__(self, ok: bool, data: Any = None, raw: Any = None, error: str = ""):
        self.ok = ok
        self.data = data
        self.raw = raw
        self.error = error


class DocRef:
    """Parsed document reference"""
    def __init__(self, kind: str, id: str = "", error: str = ""):
        self.kind = kind  # "url", "uuid", "id", "invalid"
        self.id = id
        self.error = error
