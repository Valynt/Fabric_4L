from __future__ import annotations

import httpx
import pytest

from layer4_agents.integration.connectors.core.errors import (
    AuthError,
    CRMError,
    MappingError,
    PermanentError,
    PermissionError_,
    TransientError,
    classify_http_status,
    classify_httpx_exception,
)


class TestCRMErrorTaxonomy:
    """Unit tests for the CRM error taxonomy and httpx classifiers."""

    def test_error_classes_inherit_from_crm_error(self) -> None:
        for cls in (TransientError, AuthError, PermissionError_, MappingError, PermanentError):
            assert issubclass(cls, CRMError)


class TestClassifyHttpStatus:
    """Tests for classify_http_status mapping."""

    @pytest.mark.parametrize(
        "status,expected_cls",
        [
            (401, AuthError),
            (403, PermissionError_),
            (400, PermanentError),
            (404, PermanentError),
            (422, PermanentError),
            (429, TransientError),
            (500, TransientError),
            (502, TransientError),
            (503, TransientError),
            (504, TransientError),
            (999, TransientError),
        ],
    )
    def test_status_mapping(self, status: int, expected_cls: type[CRMError]) -> None:
        result = classify_http_status(status, "boom")
        assert isinstance(result, expected_cls)
        assert "boom" in str(result)


class TestClassifyHttpxException:
    """Tests for classify_httpx_exception mapping."""

    def _make_status_error(self, status_code: int) -> httpx.HTTPStatusError:
        request = httpx.Request("GET", "https://example.com")
        response = httpx.Response(status_code, request=request)
        return httpx.HTTPStatusError("error", request=request, response=response)

    def test_http_status_error_401(self) -> None:
        exc = self._make_status_error(401)
        result = classify_httpx_exception(exc)
        assert isinstance(result, AuthError)

    def test_http_status_error_403(self) -> None:
        exc = self._make_status_error(403)
        result = classify_httpx_exception(exc)
        assert isinstance(result, PermissionError_)

    def test_http_status_error_404(self) -> None:
        exc = self._make_status_error(404)
        result = classify_httpx_exception(exc)
        assert isinstance(result, PermanentError)

    def test_http_status_error_429(self) -> None:
        exc = self._make_status_error(429)
        result = classify_httpx_exception(exc)
        assert isinstance(result, TransientError)

    def test_http_status_error_503(self) -> None:
        exc = self._make_status_error(503)
        result = classify_httpx_exception(exc)
        assert isinstance(result, TransientError)

    def test_timeout_exception(self) -> None:
        request = httpx.Request("GET", "https://example.com")
        exc = httpx.TimeoutException("timed out", request=request)
        result = classify_httpx_exception(exc)
        assert isinstance(result, TransientError)

    def test_request_error(self) -> None:
        request = httpx.Request("GET", "https://example.com")
        exc = httpx.ConnectError("connection refused", request=request)
        result = classify_httpx_exception(exc)
        assert isinstance(result, TransientError)

    def test_non_httpx_exception(self) -> None:
        exc = ValueError("bad value")
        result = classify_httpx_exception(exc)
        assert isinstance(result, PermanentError)
        assert "bad value" in str(result)
