from __future__ import annotations

import logging
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from urllib.error import HTTPError as UrllibHttpError
from urllib.error import URLError

from src.connectors.http.config import HttpConfig
from src.connectors.http.exceptions import (
    ConnectionError,
    HttpError,
    InvalidResponseError,
    InvalidUrlError,
    RedirectError,
    ResponseTooLargeError,
    TimeoutError,
)
from src.connectors.http.models import HttpMethod, Request, Response, ResponseMetadata
from src.connectors.http.retry import ExponentialBackoffRetry, RetryPolicy

log = logging.getLogger(__name__)


class HttpClient(ABC):
    """Abstract HTTP client. All connectors depend on this interface only."""

    def __init__(self, config: HttpConfig | None = None) -> None:
        self._config = config or HttpConfig()
        self._closed = False

    @property
    def config(self) -> HttpConfig:
        return self._config

    @property
    def closed(self) -> bool:
        return self._closed

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        return self.request(
            Request(
                url=url,
                method=HttpMethod.GET,
                headers=headers or {},
                params=params or {},
                timeout_override=timeout,
            )
        )

    def head(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Response:
        return self.request(
            Request(
                url=url,
                method=HttpMethod.HEAD,
                headers=headers or {},
                params=params or {},
                timeout_override=timeout,
            )
        )

    @abstractmethod
    def request(self, request: Request) -> Response: ...

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def close(self) -> None: ...


class UrllibHttpClient(HttpClient):
    """Default HTTP client backed by urllib.request (stdlib)."""

    def __init__(
        self,
        config: HttpConfig | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        super().__init__(config)
        self._retry = retry_policy or ExponentialBackoffRetry(
            max_retries=self._config.retry_count,
            base_delay=self._config.retry_delay,
        )
        self._total_requests: int = 0
        self._total_errors: int = 0

    @property
    def retry_policy(self) -> RetryPolicy:
        return self._retry

    def request(self, request: Request) -> Response:
        self._validate_url(request.url)
        self._total_requests += 1

        merged_headers = dict(self._config.default_headers)
        merged_headers.setdefault("User-Agent", self._config.user_agent)
        merged_headers.update(request.headers)

        if request.body is not None and "Content-Type" not in merged_headers:
            merged_headers.setdefault("Content-Type", "application/octet-stream")

        timeout = (
            request.timeout_override
            if request.timeout_override is not None
            else self._config.timeout
        )
        start = time.monotonic()
        last_exception: Exception | None = None
        last_response: Response | None = None
        redirect_chain: list[str] = [request.url]

        for attempt in range(self._retry.max_retries + 1):
            last_exception = None
            last_response = None

            if attempt > 0:
                delay = self._retry.delay(attempt - 1)
                log.debug(
                    "Retry %d/%d after %.2fs: %s",
                    attempt,
                    self._retry.max_retries,
                    delay,
                    request.url,
                )
                time.sleep(delay)

            try:
                response = self._execute_single(request, merged_headers, timeout, redirect_chain)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                fields = {
                    k: v
                    for k, v in response.__dict__.items()
                    if k not in ("retrieved_at", "elapsed_ms")
                }
                response = Response(**fields, elapsed_ms=elapsed_ms, retrieved_at=datetime.utcnow())
                last_response = response

                if self._retry.should_retry(attempt, response, None):
                    log.debug("Retryable status %d for %s", response.status_code, request.url)
                    continue

                log.debug(
                    "Request completed: %s %s (%d, %dms)",
                    request.method.value,
                    request.url,
                    response.status_code,
                    elapsed_ms,
                )
                return response

            except HttpError as e:
                last_exception = e
                elapsed_ms = int((time.monotonic() - start) * 1000)
                log.debug(
                    "Request failed: %s %s (%s, %dms)",
                    request.method.value,
                    request.url,
                    type(e).__name__,
                    elapsed_ms,
                )

                if self._retry.should_retry(attempt, None, e):
                    continue

                raise

        self._total_errors += 1
        if last_response is not None:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return Response(
                status_code=last_response.status_code,
                headers=last_response.headers,
                body=last_response.body,
                content_type=last_response.content_type,
                elapsed_ms=elapsed_ms,
                url=request.url,
            )

        raise last_exception or HttpError("Request failed after all retries")

    def health(self) -> dict[str, Any]:
        return {
            "available": not self._closed,
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "config": self._config.model_dump(),
            "retry_policy": type(self._retry).__name__,
        }

    def close(self) -> None:
        self._closed = True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _execute_single(
        self,
        request: Request,
        headers: dict[str, str],
        timeout: float,
        redirect_chain: list[str],
    ) -> Response:
        url = self._build_url(request.url, request.params)
        req = urllib.request.Request(
            url=url,
            data=request.body,
            headers=headers,
            method=request.method.value,
        )

        try:
            resp = urllib.request.urlopen(
                req,
                timeout=timeout,
                cafile=None,
                capath=None,
                cadefault=False,
            )
        except UrllibHttpError as e:
            status_code = e.code
            resp_headers = dict(e.headers) if e.headers else {}
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            resp_url = str(e.url) if e.url else url

            self._check_response_size(body, resp_url)

            return Response(
                status_code=status_code,
                headers=resp_headers,
                body=body,
                content_type=resp_headers.get("Content-Type", ""),
                encoding=resp_headers.get("Content-Encoding", "utf-8"),
                url=resp_url,
                metadata=ResponseMetadata(
                    content_type=resp_headers.get("Content-Type", ""),
                    content_encoding=resp_headers.get("Content-Encoding", ""),
                    redirect_count=len(redirect_chain) - 1,
                    redirect_chain=list(redirect_chain),
                ),
            )
        except URLError as e:
            reason = str(e.reason) if hasattr(e, "reason") else str(e)
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                raise TimeoutError(reason) from e
            raise ConnectionError(reason) from e
        except OSError as e:
            estr = str(e).lower()
            if "timed out" in estr or "timeout" in estr:
                raise TimeoutError(str(e)) from e
            raise ConnectionError(str(e)) from e

        status_code = resp.status
        resp_headers = dict(resp.headers) if resp.headers else {}
        body = resp.read()
        content_type = resp_headers.get("Content-Type", "")
        encoding = resp_headers.get("Content-Encoding", "utf-8")
        resp_url = str(resp.url) if hasattr(resp, "url") and resp.url else url

        self._check_response_size(body, resp_url)

        if self._config.follow_redirects and status_code in (301, 302, 303, 307, 308):
            location = resp_headers.get("Location", "")
            if not location:
                raise InvalidResponseError("Redirect response missing Location header")
            resolved = urllib.parse.urljoin(resp_url, location)
            if resolved in redirect_chain:
                raise RedirectError(f"Infinite redirect cycle detected: {resolved}")
            if len(redirect_chain) > self._config.max_redirects:
                raise RedirectError(f"Max redirects ({self._config.max_redirects}) exceeded")
            redirect_chain.append(resolved)
            follow_req = Request(
                url=resolved,
                method=request.method,
                headers=request.headers,
                params=request.params,
                body=request.body,
                timeout_override=request.timeout_override,
            )
            return self._execute_single(follow_req, headers, timeout, redirect_chain)

        return Response(
            status_code=status_code,
            headers=resp_headers,
            body=body,
            content_type=content_type,
            encoding=encoding,
            url=resp_url,
            metadata=ResponseMetadata(
                content_type=content_type,
                content_encoding=encoding,
                redirect_count=len(redirect_chain) - 1,
                redirect_chain=list(redirect_chain),
            ),
        )

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme:
            raise InvalidUrlError(f"URL missing scheme: {url}")
        if parsed.scheme not in ("http", "https"):
            raise InvalidUrlError(f"Unsupported URL scheme: {parsed.scheme}")
        if not parsed.netloc:
            raise InvalidUrlError(f"URL missing host: {url}")

    @staticmethod
    def _build_url(base: str, params: dict[str, str]) -> str:
        if not params:
            return base
        parsed = urllib.parse.urlparse(base)
        existing: dict[str, list[str]] = urllib.parse.parse_qs(parsed.query)
        for key, val in params.items():
            existing.setdefault(key, []).append(val)
        new_query = urllib.parse.urlencode(existing, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    def _check_response_size(self, body: bytes, url: str) -> None:
        if len(body) > self._config.max_response_size:
            raise ResponseTooLargeError(
                f"Response from {url} exceeds {self._config.max_response_size} bytes "
                f"(got {len(body)})"
            )
