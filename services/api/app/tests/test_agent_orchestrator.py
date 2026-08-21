from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.agent_orchestrator import (
    ERR_LAYER4_CIRCUIT_OPEN,
    ERR_LAYER4_HTTP_ERROR,
    ERR_LAYER4_INVALID_JSON,
    ERR_LAYER4_INVALID_RESPONSE_TYPE,
    ERR_LAYER4_UNAVAILABLE,
    AgentOrchestrator,
    Layer4DependencyError,
    Layer4OrchestrationClient,
    Layer4UnavailableError,
)
from value_fabric.shared.resilience import SyncCircuitBreaker


def _mock_httpx(mock_client_cls: MagicMock, response: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.request.return_value = response
    mock_client_cls.return_value = mock_client
    return mock_client


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

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_body_truncated_in_request(self, mock_client_cls: MagicMock) -> None:
        """Upstream error bodies are truncated to 400 chars."""
        long_body = "x" * 1000
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = long_body
        _mock_httpx(mock_client_cls, mock_response)

        client = Layer4OrchestrationClient(base_url="http://layer4", timeout_seconds=1.0)
        with pytest.raises(Layer4DependencyError) as exc_info:
            client.get_workflow(tenant_id="t1", workflow_id="wf-1")

        assert exc_info.value.body is not None
        assert len(exc_info.value.body) <= 400


class TestLayer4OrchestrationClient:
    def _client(self) -> Layer4OrchestrationClient:
        return Layer4OrchestrationClient(base_url="http://layer4", timeout_seconds=1.0)

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_create_workflow_posts_to_v1_workflows(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "workflow_instance_id": "wf-1",
            "status": "pending",
            "estimated_duration_seconds": 300,
        }
        mock_client = _mock_httpx(mock_client_cls, mock_response)

        result = self._client().create_workflow(
            tenant_id="t1",
            workflow_type="roi_calculator",
            account_id="acc-1",
            input_data={"foo": "bar"},
            user_id="user-1",
        )

        assert result["workflow_instance_id"] == "wf-1"
        _, kwargs = mock_client.request.call_args
        assert kwargs["json"]["workflow_type"] == "roi_calculator"
        assert kwargs["json"]["inputs"]["prospect_id"] == "acc-1"
        assert kwargs["json"]["inputs"]["custom_data"] == {"foo": "bar"}
        assert kwargs["headers"]["X-Tenant-ID"] == "t1"
        assert kwargs["headers"]["X-User-ID"] == "user-1"

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_get_workflow_success(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "wf-1", "status": "running"}
        mock_client = _mock_httpx(mock_client_cls, mock_response)

        result = self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")

        assert result == {"id": "wf-1", "status": "running"}
        args, _ = mock_client.request.call_args
        assert args[0] == "GET"
        assert args[1] == "http://layer4/v1/workflows/wf-1"

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_request_network_error_raises_unavailable(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.side_effect = httpx.ConnectError("connection refused")
        mock_client_cls.return_value = mock_client

        with pytest.raises(Layer4UnavailableError) as exc_info:
            self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")

        err = exc_info.value
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code is None

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_request_503_captures_status_code(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "service unavailable"
        _mock_httpx(mock_client_cls, mock_response)

        with pytest.raises(Layer4UnavailableError) as exc_info:
            self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")

        err = exc_info.value
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code == 503

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_request_502_captures_status_code(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.text = "bad gateway"
        _mock_httpx(mock_client_cls, mock_response)

        with pytest.raises(Layer4UnavailableError) as exc_info:
            self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")

        err = exc_info.value
        assert err.code == ERR_LAYER4_UNAVAILABLE
        assert err.status_code == 502

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_request_400_captures_status_and_body(self, mock_client_cls: MagicMock) -> None:
        body_text = '{"error": "validation failed"}'
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = body_text
        _mock_httpx(mock_client_cls, mock_response)

        with pytest.raises(Layer4DependencyError) as exc_info:
            self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")

        err = exc_info.value
        assert err.code == ERR_LAYER4_HTTP_ERROR
        assert err.status_code == 400
        assert err.body == body_text

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_request_invalid_json_raises_dependency_error(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("bad json", "", 0)
        _mock_httpx(mock_client_cls, mock_response)

        with pytest.raises(Layer4DependencyError) as exc_info:
            self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")

        err = exc_info.value
        assert err.code == ERR_LAYER4_INVALID_JSON

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_request_non_dict_response_raises_dependency_error(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["not", "a", "dict"]
        _mock_httpx(mock_client_cls, mock_response)

        with pytest.raises(Layer4DependencyError) as exc_info:
            self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")

        err = exc_info.value
        assert err.code == ERR_LAYER4_INVALID_RESPONSE_TYPE

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_pause_and_resume_send_user_context(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "paused"}
        mock_client = _mock_httpx(mock_client_cls, mock_response)

        client = self._client()
        client.pause_workflow(tenant_id="t1", workflow_id="wf-1", user_id="user-1")
        _, kwargs = mock_client.request.call_args
        assert kwargs["json"]["user_id"] == "user-1"
        assert kwargs["json"]["tenant_id"] == "t1"

        client.resume_workflow(tenant_id="t1", workflow_id="wf-1", user_id="user-1")
        _, kwargs = mock_client.request.call_args
        assert kwargs["json"]["user_id"] == "user-1"

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_cancel_uses_delete(self, mock_client_cls: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"workflow_id": "wf-1", "status": "cancelled"}
        mock_client = _mock_httpx(mock_client_cls, mock_response)

        result = self._client().cancel_workflow(tenant_id="t1", workflow_id="wf-1")

        assert result["status"] == "cancelled"
        args, _ = mock_client.request.call_args
        assert args[0] == "DELETE"


class TestLayer4OrchestrationClientResilience:
    """Retry with backoff and circuit breaker for transient Layer 4 failures."""

    def _client(self, **kwargs) -> Layer4OrchestrationClient:
        return Layer4OrchestrationClient(
            base_url="http://layer4",
            timeout_seconds=1.0,
            max_attempts=kwargs.get("max_attempts", 3),
            retry_base_delay=0.0,
            retry_max_delay=0.0,
            sleep=lambda _: None,
            breaker=kwargs.get(
                "breaker",
                SyncCircuitBreaker(
                    "layer4-test", failure_threshold=5, recovery_timeout=60.0
                ),
            ),
        )

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_transient_503_retried_then_succeeds(self, mock_client_cls: MagicMock) -> None:
        """A 503 followed by a 200 succeeds after retries."""
        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"id": "wf-1", "status": "running"}
        bad_response = MagicMock()
        bad_response.status_code = 503
        bad_response.text = "unavailable"

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.side_effect = [bad_response, ok_response]
        mock_client_cls.return_value = mock_client

        result = self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")
        assert result == {"id": "wf-1", "status": "running"}
        assert mock_client.request.call_count == 2

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_transient_503_exhausts_attempts_raises_unavailable(
        self, mock_client_cls: MagicMock
    ) -> None:
        """Persistent 503 exhausts retries and raises Layer4UnavailableError."""
        bad_response = MagicMock()
        bad_response.status_code = 503
        bad_response.text = "unavailable"

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.return_value = bad_response
        mock_client_cls.return_value = mock_client

        with pytest.raises(Layer4UnavailableError) as exc_info:
            self._client(max_attempts=3).get_workflow(
                tenant_id="t1", workflow_id="wf-1"
            )
        assert exc_info.value.code == ERR_LAYER4_UNAVAILABLE
        assert exc_info.value.status_code == 503
        assert mock_client.request.call_count == 3

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_network_error_retried(self, mock_client_cls: MagicMock) -> None:
        """ConnectError is retryable; success on second attempt."""
        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"id": "wf-1", "status": "running"}

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.side_effect = [
            httpx.ConnectError("connection refused"),
            ok_response,
        ]
        mock_client_cls.return_value = mock_client

        result = self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")
        assert result["id"] == "wf-1"
        assert mock_client.request.call_count == 2

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_4xx_not_retried(self, mock_client_cls: MagicMock) -> None:
        """Deterministic 4xx failures surface immediately without retry."""
        bad_response = MagicMock()
        bad_response.status_code = 400
        bad_response.text = '{"detail": "bad request"}'

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.return_value = bad_response
        mock_client_cls.return_value = mock_client

        with pytest.raises(Layer4DependencyError):
            self._client().get_workflow(tenant_id="t1", workflow_id="wf-1")
        assert mock_client.request.call_count == 1

    @patch("app.services.agent_orchestrator.httpx.Client")
    def test_circuit_open_raises_unavailable(self, mock_client_cls: MagicMock) -> None:
        """When the breaker is open, requests fail fast with circuit_open code."""
        breaker = SyncCircuitBreaker(
            "layer4-open", failure_threshold=1, recovery_timeout=300.0
        )
        client = self._client(breaker=breaker)

        bad_response = MagicMock()
        bad_response.status_code = 503
        bad_response.text = "down"
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.request.return_value = bad_response
        mock_client_cls.return_value = mock_client

        # First call: the first HTTP attempt fails (503) and opens the
        # breaker (threshold=1). Subsequent retry attempts within this
        # call are rejected by the open breaker. The call surfaces as
        # Layer4UnavailableError with the circuit_open code.
        with pytest.raises(Layer4UnavailableError) as exc_info:
            client.get_workflow(tenant_id="t1", workflow_id="wf-1")
        assert exc_info.value.code == ERR_LAYER4_CIRCUIT_OPEN
        assert breaker.state == "open"
        # Only one HTTP request was made (the breaker rejected the retry).
        assert mock_client.request.call_count == 1

        # Second call: breaker still open → fail fast, no HTTP attempt.
        with pytest.raises(Layer4UnavailableError) as exc_info2:
            client.get_workflow(tenant_id="t1", workflow_id="wf-1")
        assert exc_info2.value.code == ERR_LAYER4_CIRCUIT_OPEN
        # Still only the original HTTP request — no new attempts.
        assert mock_client.request.call_count == 1


class FakeLayer4Client:
    """In-memory stand-in for Layer4OrchestrationClient delegation tests."""

    provider_name = "layer4"

    def __init__(self) -> None:
        self.workflows: dict[str, dict] = {}

    def create_workflow(self, *, tenant_id, workflow_type, account_id, input_data, user_id=None):
        workflow_id = f"wf-{len(self.workflows) + 1}"
        self.workflows[workflow_id] = {
            "workflow_instance_id": workflow_id,
            "status": "pending",
            "tenant_id": tenant_id,
            "workflow_type": workflow_type,
        }
        return self.workflows[workflow_id]

    def get_workflow(self, *, tenant_id, workflow_id):
        if workflow_id not in self.workflows:
            raise Layer4DependencyError(
                ERR_LAYER4_HTTP_ERROR, status_code=404, body="not found"
            )
        return self.workflows[workflow_id]

    def pause_workflow(self, *, tenant_id, workflow_id, user_id, reason=None):
        self.workflows[workflow_id]["status"] = "paused"
        return self.workflows[workflow_id]

    def resume_workflow(self, *, tenant_id, workflow_id, user_id, resume_data=None):
        self.workflows[workflow_id]["status"] = "running"
        return self.workflows[workflow_id]

    def cancel_workflow(self, *, tenant_id, workflow_id):
        self.workflows[workflow_id]["status"] = "cancelled"
        return self.workflows[workflow_id]


class TestAgentOrchestratorDelegation:
    # Tenant-context hardening requires UUID-format tenant ids on the
    # projection store path (require_tenant_context); "t1" no longer passes.
    TENANT = "00000000-0000-4000-8000-00000000d001"

    def _orchestrator(self) -> AgentOrchestrator:
        return AgentOrchestrator(layer4_client=FakeLayer4Client())

    def test_create_run_delegates_and_projects(self) -> None:
        orchestrator = self._orchestrator()
        run = orchestrator.create_run(
            tenant_id=self.TENANT, workflow_type="roi_calculator", account_id="acc-1"
        )
        assert run.id == "wf-1"
        assert run.status == "pending"
        assert run.output["projection"] == "derived-from-layer4-workflow"

    def test_get_run_refreshes_from_layer4(self) -> None:
        orchestrator = self._orchestrator()
        run = orchestrator.create_run(tenant_id=self.TENANT, workflow_type="roi_calculator")
        orchestrator.layer4_client.workflows[run.id]["status"] = "running"
        refreshed = orchestrator.get_run(run.id, tenant_id=self.TENANT)
        assert refreshed is not None
        assert refreshed.status == "running"

    def test_get_run_missing_projection_returns_none(self) -> None:
        orchestrator = self._orchestrator()
        assert orchestrator.get_run("wf-missing", tenant_id=self.TENANT) is None

    def test_pause_resume_cancel_delegate(self) -> None:
        orchestrator = self._orchestrator()
        run = orchestrator.create_run(tenant_id=self.TENANT, workflow_type="roi_calculator")

        paused = orchestrator.pause_run(run.id, tenant_id=self.TENANT, user_id="u1")
        assert paused.status == "paused"

        resumed = orchestrator.resume_run(run.id, tenant_id=self.TENANT, user_id="u1")
        assert resumed.status == "running"

        cancelled = orchestrator.cancel_run(run.id, tenant_id=self.TENANT)
        assert cancelled.status == "cancelled"

    def test_unknown_status_maps_to_default(self) -> None:
        orchestrator = self._orchestrator()
        run = orchestrator.create_run(tenant_id=self.TENANT, workflow_type="roi_calculator")
        orchestrator.layer4_client.workflows[run.id]["status"] = "weird-state"
        refreshed = orchestrator.get_run(run.id, tenant_id=self.TENANT)
        assert refreshed is not None
        assert refreshed.status == "pending"
