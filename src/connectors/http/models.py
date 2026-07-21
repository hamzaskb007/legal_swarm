from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HttpMethod(StrEnum):
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"


class HttpVersion(StrEnum):
    HTTP_1_0 = "HTTP/1.0"
    HTTP_1_1 = "HTTP/1.1"
    HTTP_2 = "HTTP/2"
    HTTP_3 = "HTTP/3"


class Request(BaseModel, frozen=True):
    url: str
    method: HttpMethod = HttpMethod.GET
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    body: bytes | None = None
    timeout_override: float | None = None


class ResponseMetadata(BaseModel, frozen=True):
    elapsed_ms: int = 0
    response_size: int = 0
    redirect_count: int = 0
    redirect_chain: list[str] = Field(default_factory=list)
    content_type: str = ""
    content_encoding: str = ""
    http_version: HttpVersion = HttpVersion.HTTP_1_1


class Response(BaseModel, frozen=True):
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: bytes = b""
    content_type: str = ""
    encoding: str = "utf-8"
    elapsed_ms: int = 0
    response_size: int = 0
    url: str = ""
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def text(self) -> str:
        try:
            return self.body.decode(self.encoding)
        except (UnicodeDecodeError, LookupError):
            return self.body.decode("utf-8", errors="replace")

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)
