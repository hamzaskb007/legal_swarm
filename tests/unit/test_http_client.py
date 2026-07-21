"""Unit tests for the HTTP Client abstraction."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.connectors.http.client import HttpClient, UrllibHttpClient
from src.connectors.http.config import HttpConfig
from src.connectors.http.exceptions import (
    ConnectionError,
    HttpError,
    InvalidResponseError,
    InvalidUrlError,
    RedirectError,
    ResponseTooLargeError,
    TimeoutError,
    UnsupportedMimeTypeError,
)
from src.connectors.http.models import HttpMethod, Request, Response, ResponseMetadata
from src.connectors.http.retry import (
    ExponentialBackoffRetry,
    NoRetry,
)

# ===================================================================
# Models
# ===================================================================


class TestRequest:
    def test_defaults(self):
        r = Request(url="https://example.gov")
        assert r.url == "https://example.gov"
        assert r.method == HttpMethod.GET
        assert r.headers == {}
        assert r.params == {}
        assert r.body is None
        assert r.timeout_override is None

    def test_frozen(self):
        r = Request(url="https://example.gov")
        with pytest.raises(Exception):
            r.url = "changed"

    def test_with_all_fields(self):
        r = Request(
            url="https://example.gov/api",
            method=HttpMethod.POST,
            headers={"Authorization": "Bearer x"},
            params={"q": "test"},
            body=b'{"key": "value"}',
            timeout_override=15.0,
        )
        assert r.method == HttpMethod.POST
        assert r.body == b'{"key": "value"}'


class TestResponse:
    def test_defaults(self):
        resp = Response(status_code=200)
        assert resp.status_code == 200
        assert resp.body == b""
        assert resp.ok is True
        assert resp.is_redirect is False

    def test_frozen(self):
        resp = Response(status_code=200)
        with pytest.raises(Exception):
            resp.status_code = 404

    def test_text_decodes_body(self):
        resp = Response(status_code=200, body=b"hello", encoding="utf-8")
        assert resp.text == "hello"

    def test_text_fallback_on_decode_error(self):
        resp = Response(status_code=200, body=b"\xff\xfe", encoding="utf-8")
        assert isinstance(resp.text, str)

    def test_ok_property(self):
        assert Response(status_code=200).ok is True
        assert Response(status_code=201).ok is True
        assert Response(status_code=301).ok is False
        assert Response(status_code=404).ok is False
        assert Response(status_code=500).ok is False

    def test_is_redirect(self):
        assert Response(status_code=301).is_redirect is True
        assert Response(status_code=302).is_redirect is True
        assert Response(status_code=200).is_redirect is False
        assert Response(status_code=404).is_redirect is False


# ===================================================================
# Exception hierarchy
# ===================================================================


class TestHttpExceptions:
    def test_http_error_inherits_from_connector_error(self):
        from src.connectors.exceptions import ConnectorError

        assert issubclass(HttpError, ConnectorError)

    def test_all_exceptions_inherit_from_http_error(self):
        assert issubclass(TimeoutError, HttpError)
        assert issubclass(RedirectError, HttpError)
        assert issubclass(ConnectionError, HttpError)
        assert issubclass(InvalidResponseError, HttpError)
        assert issubclass(UnsupportedMimeTypeError, HttpError)
        assert issubclass(ResponseTooLargeError, HttpError)
        assert issubclass(InvalidUrlError, HttpError)

    def test_http_configuration_error_inherits_from_http_error(self):
        from src.connectors.http.exceptions import HttpConfigurationError

        assert issubclass(HttpConfigurationError, HttpError)

    def test_message_preserved(self):
        try:
            raise TimeoutError("custom timeout")
        except TimeoutError as e:
            assert str(e) == "custom timeout"


# ===================================================================
# Retry policy
# ===================================================================


class TestExponentialBackoffRetry:
    def test_defaults(self):
        retry = ExponentialBackoffRetry()
        assert retry.max_retries == 3

    def test_should_retry_on_retryable_status(self):
        retry = ExponentialBackoffRetry(max_retries=3)
        resp = Response(status_code=500)
        assert retry.should_retry(attempt=0, response=resp, exception=None)

    def test_should_not_retry_on_success(self):
        retry = ExponentialBackoffRetry(max_retries=3)
        resp = Response(status_code=200)
        assert not retry.should_retry(attempt=0, response=resp, exception=None)

    def test_should_not_retry_on_non_retryable_status(self):
        retry = ExponentialBackoffRetry(max_retries=3)
        resp = Response(status_code=400)
        assert not retry.should_retry(attempt=0, response=resp, exception=None)

    def test_should_retry_on_retryable_exception(self):
        retry = ExponentialBackoffRetry(max_retries=3)
        assert retry.should_retry(attempt=0, response=None, exception=TimeoutError("timeout"))
        assert retry.should_retry(attempt=0, response=None, exception=ConnectionError("refused"))

    def test_should_not_retry_on_non_retryable_exception(self):
        retry = ExponentialBackoffRetry(max_retries=3)
        assert not retry.should_retry(attempt=0, response=None, exception=ValueError("bad"))

    def test_exhausts_retries(self):
        retry = ExponentialBackoffRetry(max_retries=2)
        resp = Response(status_code=503)
        assert retry.should_retry(attempt=0, response=resp, exception=None)
        assert retry.should_retry(attempt=1, response=resp, exception=None)
        assert not retry.should_retry(attempt=2, response=resp, exception=None)

    def test_delay_exponential(self):
        retry = ExponentialBackoffRetry(max_retries=3, base_delay=1.0)
        assert retry.delay(0) == 1.0
        assert retry.delay(1) == 2.0
        assert retry.delay(2) == 4.0

    def test_invalid_max_retries(self):
        with pytest.raises(ValueError):
            ExponentialBackoffRetry(max_retries=-1)

    def test_invalid_base_delay(self):
        with pytest.raises(ValueError):
            ExponentialBackoffRetry(base_delay=0)


class TestNoRetry:
    def test_never_retries(self):
        retry = NoRetry()
        assert retry.max_retries == 0
        resp = Response(status_code=500)
        assert not retry.should_retry(attempt=0, response=resp, exception=None)
        assert not retry.should_retry(attempt=0, response=None, exception=TimeoutError("x"))


# ===================================================================
# HttpConfig
# ===================================================================


class TestHttpConfig:
    def test_defaults(self):
        cfg = HttpConfig()
        assert cfg.timeout == 30.0
        assert cfg.connect_timeout == 10.0
        assert cfg.read_timeout == 20.0
        assert cfg.max_redirects == 5
        assert cfg.retry_count == 3
        assert cfg.retry_delay == 1.0
        assert cfg.max_response_size == 10 * 1024 * 1024
        assert cfg.follow_redirects is True
        assert cfg.verify_ssl is True

    def test_frozen(self):
        cfg = HttpConfig()
        with pytest.raises(Exception):
            cfg.timeout = 60.0

    def test_custom_values(self):
        cfg = HttpConfig(timeout=60.0, max_redirects=10, retry_count=5)
        assert cfg.timeout == 60.0
        assert cfg.max_redirects == 10
        assert cfg.retry_count == 5

    def test_user_agent_default(self):
        cfg = HttpConfig()
        assert "LegalSwarm" in cfg.user_agent


# ===================================================================
# HttpClient abstract
# ===================================================================


class TestHttpClientAbstract:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            HttpClient()  # type: ignore[abstract]

    def test_default_config(self):
        class _Minimal(HttpClient):
            def request(self, request: Request) -> Response:
                return Response(status_code=200)

            def health(self) -> dict[str, Any]:
                return {}

            def close(self) -> None:
                pass

        client = _Minimal()
        assert isinstance(client.config, HttpConfig)
        assert client.closed is False

    def test_custom_config(self):
        class _Minimal(HttpClient):
            def request(self, request: Request) -> Response:
                return Response(status_code=200)

            def health(self) -> dict[str, Any]:
                return {}

            def close(self) -> None:
                pass

        cfg = HttpConfig(timeout=99.0)
        client = _Minimal(config=cfg)
        assert client.config.timeout == 99.0


# ===================================================================
# UrllibHttpClient — validation tests
# ===================================================================


class TestUrllibHttpClientValidation:
    def test_default_construction(self):
        client = UrllibHttpClient()
        assert isinstance(client.config, HttpConfig)
        assert isinstance(client.retry_policy, ExponentialBackoffRetry)
        assert client.closed is False

    def test_health_returns_dict(self):
        client = UrllibHttpClient()
        h = client.health()
        assert "available" in h
        assert "total_requests" in h
        assert h["available"] is True

    def test_close(self):
        client = UrllibHttpClient()
        client.close()
        assert client.closed is True
        h = client.health()
        assert h["available"] is False

    def test_validate_url_missing_scheme(self):
        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(InvalidUrlError, match="scheme"):
            client.request(Request(url="no-scheme.gov"))

    def test_validate_url_bad_scheme(self):
        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(InvalidUrlError, match="scheme"):
            client.request(Request(url="ftp://files.gov"))

    def test_validate_url_missing_host(self):
        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(InvalidUrlError, match="host"):
            client.request(Request(url="https://"))

    def test_validate_url_empty(self):
        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(InvalidUrlError):
            client.request(Request(url=""))

    def test_get_convenience(self):
        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(InvalidUrlError):
            client.get("not-a-url")

    def test_head_convenience(self):
        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(InvalidUrlError):
            client.head("bad")

    def test_retry_count_from_config(self):
        cfg = HttpConfig(retry_count=5)
        retry = ExponentialBackoffRetry(max_retries=cfg.retry_count)
        client = UrllibHttpClient(config=cfg, retry_policy=retry)
        assert client.retry_policy.max_retries == 5

    def test_no_retry_policy(self):
        retry = NoRetry()
        client = UrllibHttpClient(retry_policy=retry)
        assert isinstance(client.retry_policy, NoRetry)

    def test_request_frozen(self):
        r = Request(url="https://example.gov")
        with pytest.raises(Exception):
            r.url = "changed"


# ===================================================================
# UrllibHttpClient — mocked request tests
# ===================================================================


class TestUrllibHttpClientMocked:
    """Tests using mocked urllib requests."""

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_successful_get(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.read.return_value = b"<html>ok</html>"
        mock_urlopen.return_value = mock_response

        client = UrllibHttpClient(retry_policy=NoRetry())
        resp = client.get("https://example.gov")
        assert resp.status_code == 200
        assert resp.body == b"<html>ok</html>"
        assert resp.ok is True

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_successful_head(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.read.return_value = b""
        mock_urlopen.return_value = mock_response

        client = UrllibHttpClient(retry_policy=NoRetry())
        resp = client.head("https://example.gov")
        assert resp.status_code == 200

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_get_with_params(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b"{}"
        mock_urlopen.return_value = mock_response

        client = UrllibHttpClient(retry_policy=NoRetry())
        client.get("https://example.gov/api", params={"q": "test", "page": "1"})
        called_url = mock_req.call_args[1].get("url", "")
        assert "q=test" in called_url
        assert "page=1" in called_url

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_http_error_status(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        from io import BytesIO
        from urllib.error import HTTPError as UrllibHttpError

        def _raise(*args: Any, **kwargs: Any) -> None:
            raise UrllibHttpError("https://example.gov/404", 404, "Not Found", {}, BytesIO(b""))

        mock_urlopen.side_effect = _raise

        client = UrllibHttpClient(retry_policy=NoRetry())
        resp = client.get("https://example.gov/404")
        assert resp.status_code == 404
        assert resp.ok is False

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_connection_refused(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        from urllib.error import URLError

        def _raise(*args: Any, **kwargs: Any) -> None:
            raise URLError("Connection refused")

        mock_urlopen.side_effect = _raise

        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(ConnectionError):
            client.get("https://example.gov")

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_timeout(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        from urllib.error import URLError

        def _raise(*args: Any, **kwargs: Any) -> None:
            raise URLError("timed out")

        mock_urlopen.side_effect = _raise

        client = UrllibHttpClient(retry_policy=NoRetry())
        with pytest.raises(TimeoutError):
            client.get("https://example.gov")

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_retry_then_succeed(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        from io import BytesIO
        from urllib.error import HTTPError as UrllibHttpError

        call_count: list[int] = [0]

        def side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                raise UrllibHttpError(
                    "https://example.gov", 503, "Service Unavailable", {}, BytesIO(b"")
                )
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.headers = {}
            mock_resp.read.return_value = b"ok"
            return mock_resp

        mock_urlopen.side_effect = side_effect

        retry = ExponentialBackoffRetry(max_retries=2, base_delay=0.01)
        client = UrllibHttpClient(retry_policy=retry)
        resp = client.get("https://example.gov")
        assert resp.status_code == 200
        assert call_count[0] == 2

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_retry_exhausted_returns_last_response(
        self, mock_req: MagicMock, mock_urlopen: MagicMock
    ) -> None:
        from io import BytesIO
        from urllib.error import HTTPError as UrllibHttpError

        def side_effect(*args: Any, **kwargs: Any) -> None:
            raise UrllibHttpError(
                "https://example.gov", 503, "Service Unavailable", {}, BytesIO(b"")
            )

        mock_urlopen.side_effect = side_effect

        retry = ExponentialBackoffRetry(max_retries=1, base_delay=0.01)
        client = UrllibHttpClient(retry_policy=retry)
        resp = client.get("https://example.gov")
        assert resp.status_code == 503

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_user_agent_header(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.read.return_value = b""
        mock_urlopen.return_value = mock_response

        client = UrllibHttpClient(
            config=HttpConfig(user_agent="CustomAgent/1.0"),
            retry_policy=NoRetry(),
        )
        client.get("https://example.gov")
        called_headers = mock_req.call_args[1].get("headers", {})
        assert called_headers.get("User-Agent") == "CustomAgent/1.0"

    @patch("src.connectors.http.client.urllib.request.urlopen")
    @patch("src.connectors.http.client.urllib.request.Request")
    def test_redirect_handling(self, mock_req: MagicMock, mock_urlopen: MagicMock) -> None:
        from io import BytesIO
        from urllib.error import HTTPError as UrllibHttpError

        def side_effect(*args: Any, **kwargs: Any) -> None:
            raise UrllibHttpError(
                "https://example.gov/old",
                302,
                "Moved",
                {"Location": "https://example.gov/new"},
                BytesIO(b""),
            )

        mock_urlopen.side_effect = side_effect

        client = UrllibHttpClient(config=HttpConfig(follow_redirects=True), retry_policy=NoRetry())
        resp = client.get("https://example.gov/old")
        assert resp.status_code == 302


# ===================================================================
# Edge cases
# ===================================================================


class TestEdgeCases:
    def test_oserror_timeout(self) -> None:
        client = UrllibHttpClient(retry_policy=NoRetry())
        with patch("src.connectors.http.client.urllib.request.urlopen") as mock:
            mock.side_effect = OSError("Operation timed out")
            with pytest.raises(TimeoutError):
                client.get("https://example.gov")

    def test_oserror_connection(self) -> None:
        client = UrllibHttpClient(retry_policy=NoRetry())
        with patch("src.connectors.http.client.urllib.request.urlopen") as mock:
            mock.side_effect = OSError("Connection reset by peer")
            with pytest.raises(ConnectionError):
                client.get("https://example.gov")

    def test_build_url_with_params(self) -> None:
        url = UrllibHttpClient._build_url("https://example.gov", {"q": "test"})
        assert "q=test" in url

    def test_build_url_no_params(self) -> None:
        url = UrllibHttpClient._build_url("https://example.gov", {})
        assert url == "https://example.gov"

    def test_check_response_size_under_limit(self) -> None:
        client = UrllibHttpClient(config=HttpConfig(max_response_size=100), retry_policy=NoRetry())
        client._check_response_size(b"x" * 50, "https://example.gov")

    def test_check_response_size_over_limit(self) -> None:
        client = UrllibHttpClient(config=HttpConfig(max_response_size=10), retry_policy=NoRetry())
        with pytest.raises(ResponseTooLargeError):
            client._check_response_size(b"x" * 100, "https://example.gov")

    def test_response_too_large_exception_raise(self) -> None:
        with pytest.raises(ResponseTooLargeError):
            raise ResponseTooLargeError("too big")


class TestResponseProperties:
    def test_no_redirect(self) -> None:
        resp = Response(status_code=200)
        assert resp.metadata.redirect_count == 0
        assert resp.metadata.redirect_chain == []

    def test_with_redirect_metadata(self) -> None:
        meta = ResponseMetadata(
            elapsed_ms=150,
            response_size=1024,
            redirect_count=1,
            redirect_chain=["https://a.gov", "https://b.gov"],
            content_type="text/html",
            content_encoding="gzip",
        )
        resp = Response(status_code=200, metadata=meta)
        assert resp.metadata.redirect_count == 1
        assert resp.metadata.redirect_chain == ["https://a.gov", "https://b.gov"]
