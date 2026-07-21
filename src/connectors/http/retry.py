from __future__ import annotations

from abc import ABC, abstractmethod

from src.connectors.http.config import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_DELAY
from src.connectors.http.exceptions import ConnectionError, TimeoutError
from src.connectors.http.models import Response


RETRYABLE_STATUS_CODES: frozenset[int] = frozenset(
    {
        429,
        500,
        502,
        503,
        504,
    }
)

RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    TimeoutError,
    ConnectionError,
)


class RetryPolicy(ABC):
    """Replaceable strategy for HTTP retry logic."""

    @property
    @abstractmethod
    def max_retries(self) -> int: ...

    @abstractmethod
    def should_retry(
        self,
        attempt: int,
        response: Response | None,
        exception: Exception | None,
    ) -> bool: ...

    @abstractmethod
    def delay(self, attempt: int) -> float: ...


class ExponentialBackoffRetry(RetryPolicy):
    """Exponential backoff with jitter-free deterministic delays."""

    def __init__(
        self,
        max_retries: int = DEFAULT_RETRY_COUNT,
        base_delay: float = DEFAULT_RETRY_DELAY,
        retryable_status_codes: frozenset[int] = RETRYABLE_STATUS_CODES,
        retryable_exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if base_delay <= 0:
            raise ValueError("base_delay must be > 0")
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._retryable_status_codes = retryable_status_codes
        self._retryable_exceptions = retryable_exceptions

    @property
    def max_retries(self) -> int:
        return self._max_retries

    def should_retry(
        self,
        attempt: int,
        response: Response | None,
        exception: Exception | None,
    ) -> bool:
        if attempt >= self._max_retries:
            return False

        if response is not None:
            return response.status_code in self._retryable_status_codes

        if exception is not None:
            return isinstance(exception, self._retryable_exceptions)

        return False

    def delay(self, attempt: int) -> float:
        return float(self._base_delay * (2**attempt))


class NoRetry(RetryPolicy):
    """Retry policy that never retries."""

    @property
    def max_retries(self) -> int:
        return 0

    def should_retry(
        self,
        attempt: int,
        response: Response | None,
        exception: Exception | None,
    ) -> bool:
        return False

    def delay(self, attempt: int) -> float:
        return 0.0
