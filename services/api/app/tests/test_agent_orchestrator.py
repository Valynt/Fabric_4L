from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.agent_orchestrator import (
    ERR_LAYER4_HTTP_ERROR,
    ERR_LAYER4_INVALID_JSON,
    ERR_LAYER4_INVALID_RESPONSE_TYPE,
    ERR_LAYER4_UNAVAILABLE,
    Layer4DependencyError,
    Layer4OrchestrationClient,
    Layer4UnavailableError,
)


class TestLayer4UnavailableError:
    def test_stores_code_without_status(self) -> None:
        err = Layer4UnavailableError(ERR_LAYER4_UNAVAILABLE)
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code is None
        assert str(err) == ERR_LAYER4_UNAVAILABLE

    def test_stores_status_code_when_provided(self) -> None:
        err = Layer4UnavailableError(ERR_LAYER4_UNAVAILABLE, status_code=503)
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code == 503


class TestLayer4DependencyError:
    def test_stores_code_and_status_and_body(self) -> None:
        err = Layer4DependencyError(
            ERR_LAYER4_HTTP_ERROR,
            status_code=422,
            body='{"detail": "bad request"}',
        )
        assert err.code == ERR_LAYER4_HTTP_ERROR
        assert err.status_code == 422
        assert err.body == '{"detail": "bad request"}'

    def test_body_stored_as_provided(self) -> None:
        long_body = "x" * 1000
        err = Layer4DependencyError(ERR_LAYER4_HTTP_ERROR, body=long_body)
        assert err.body == long_body

    def test_body_truncated_in_execute_step(self) -> None:
        """execute_step truncates response body to 400 chars."""
        long_body = "x" * 1000
        with patch("app.services.agent_orchestrator.httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = long_body

            mock_client = MagicMock()
            mock_client.__enter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            client = Layer4OrchestrationClient(base_url="http://layer4", timeout_seconds=1.0)
            with pytest.raises(Layer4DependencyError) as exc_info:
                client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

            assert exc_info.value.body is not None
            assert len(exc_info.value.body) <= 400


class TestLayer4OrchestrationClient:
    def _client(self) -> Layer4OrchestrationClient:
        return Layer4OrchestrationClient(base_url="http://layer4", timeout_seconds=1.0)

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_success(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "ok"}
        mock_response.text = '{"result": "ok"}'

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = self._client()
        result = client.execute_step(
            tenant_id="t1",
            run_id="r1",
            step_name="step",
            tool_name="tool",
        )
        assert result == {"result": "ok"}

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_network_error_raises_unavailable(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_client_cls.return_value = mock_client

        client = self._client()
        with pytest.raises(Layer4UnavailableError) as exc_info:
            client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

        err = exc_info.value
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code is None

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_503_captures_status_code(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "service unavailable"

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = self._client()
        with pytest.raises(Layer4UnavailableError) as exc_info:
            client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

        err = exc_info.value
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code == 503

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_502_captures_status_code(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.text = "bad gateway"

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = self._client()
        with pytest.raises(Layer4UnavailableError) as exc_info:
            client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

        err = exc_info.value
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code == 502

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_400_captures_status_and_body(self, mock_client_cls: MagicMock) -> None:
        body_text = '{"error": "validation failed"}'
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = body_text

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = self._client()
        with pytest.raises(Layer4DependencyError) as exc_info:
            client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

        err = exc_info.value
        assert err.code == ERR_LAYER4_HTTP_ERROR
        assert err.status_code == 400
        assert err.body == body_text

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_body_truncated(self, mock_client_cls: MagicMock) -> None:
        long_body = "x" * 1000
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = long_body

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = self._client()
        with pytest.raises(Layer4DependencyError) as exc_info:
            client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

        err = exc_info.value
        assert err.body is not None
        assert len(err.body) <= 400

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_invalid_json_raises_dependency_error(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("bad json", "", 0)

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = self._client()
        with pytest.raises(Layer4DependencyError) as exc_info:
            client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

        err = exc_info.value
        assert err.code == ERR_LAYER4_INVALID_JSON

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_execute_step_non_dict_response_raises_dependency_error(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["not", "a", "dict"]

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = self._client()
        with pytest.raises(Layer4DependencyError) as exc_info:
            client.execute_step(tenant_id="t1", run_id="r1", step_name="step", tool_name="tool")

        err = exc_info.value
        assert err.code == ERR_LAYER4_INVALID_RESPONSE_TYPE
