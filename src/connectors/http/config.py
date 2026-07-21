from __future__ import annotations

from pydantic import BaseModel, Field


DEFAULT_USER_AGENT = "LegalSwarm/1.0 (+https://github.com/anomalyco/legal-swarm)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 20.0
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_MAX_RESPONSE_SIZE = 10 * 1024 * 1024


class HttpConfig(BaseModel, frozen=True):
    timeout: float = DEFAULT_TIMEOUT
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    read_timeout: float = DEFAULT_READ_TIMEOUT
    follow_redirects: bool = True
    max_redirects: int = DEFAULT_MAX_REDIRECTS
    retry_count: int = DEFAULT_RETRY_COUNT
    retry_delay: float = DEFAULT_RETRY_DELAY
    max_response_size: int = DEFAULT_MAX_RESPONSE_SIZE
    default_headers: dict[str, str] = Field(default_factory=dict)
    user_agent: str = DEFAULT_USER_AGENT
    verify_ssl: bool = True
    pool_connections: int = 10
    pool_maxsize: int = 10
