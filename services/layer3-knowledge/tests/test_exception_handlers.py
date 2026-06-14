"""Targeted tests for API exception handler logging behaviour."""

from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from src.api.exceptions import ValueFabricException
from src.api.main import (
    global_exception_handler,
    value_fabric_exception_handler,
)


def _make_request() -> Request:
    app = MagicMock()
    app.state = MagicMock()
    app.state.metrics = None
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
        "app": app,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_value_fabric_exception_handler_logs_with_explicit_exc_info_tuple():
    request = _make_request()
    exc = ValueFabricException("boom", error_code="INTERNAL_ERROR")

    with patch("src.api.main.logger.error") as mock_error:
        response = await value_fabric_exception_handler(request, exc)

    assert response.status_code == 500
    assert mock_error.call_count == 1

    _, kwargs = mock_error.call_args
    exc_info = kwargs.get("exc_info")
    assert isinstance(exc_info, tuple)
    assert len(exc_info) == 3
    assert exc_info[0] is ValueFabricException
    assert exc_info[1] is exc


@pytest.mark.asyncio
async def test_global_exception_handler_logs_with_explicit_exc_info_tuple():
    request = _make_request()
    exc = RuntimeError("unexpected")

    with patch("src.api.main.logger.error") as mock_error:
        response = await global_exception_handler(request, exc)

    assert response.status_code == 500
    assert mock_error.call_count == 1

    _, kwargs = mock_error.call_args
    exc_info = kwargs.get("exc_info")
    assert isinstance(exc_info, tuple)
    assert len(exc_info) == 3
    assert exc_info[0] is RuntimeError
    assert exc_info[1] is exc
