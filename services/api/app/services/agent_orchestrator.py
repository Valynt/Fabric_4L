"""Gateway delegation to the Layer 4 workflow engine.

The gateway does not execute agent workflows itself. Every run created
through the gateway delegates to the Layer 4 ``/v1/workflows`` API (the
owning service, decision D2 in docs/architecture/source-of-truth-ratification.md).
The local ``db.agent_runs`` store is a rebuildable projection of Layer 4
workflow state, refreshed on read and on lifecycle calls; it is never the
authority for workflow truth.

If Layer 4 is unavailable the gateway fails closed (503) rather than
returning record-only success responses.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Mapping

import httpx
from value_fabric.shared.observability.http_trace_propagation import (
    inject_trace_headers,
)
from value_fabric.shared.resilience import (
    TRANSIENT_STATUS_CODES,
    RetryableError,
    SyncCircuitBreaker,
    SyncCircuitBreakerOpen,
    retry_transient,
)

from app.core.config import get_settings
from app.core.database import db
from app.models.schemas import AgentRun

# Error codes for agent orchestrator operations
ERR_LAYER4_UNAVAILABLE = "layer4_unavailable"
ERR_LAYER4_HTTP_ERROR = "layer4_http_error"
ERR_LAYER4_INVALID_JSON = "layer4_invalid_json"
ERR_LAYER4_INVALID_RESPONSE_TYPE = "layer4_invalid_response_type"
ERR_RUN_NOT_FOUND = "run_not_found"
ERR_LAYER4_CIRCUIT_OPEN = "layer4_circuit_open"

logger = logging.getLogger(__name__)

# Retry configuration for transient Layer 4 failures (502/503/504/429 and
# network errors). Tunable via env for production ops without code changes.
_DEFAULT_MAX_ATTEMPTS = int(os.environ.get("LAYER4_RETRY_MAX_ATTEMPTS", "3"))
_DEFAULT_RETRY_BASE_DELAY = float(os.environ.get("LAYER4_RETRY_BASE_DELAY", "0.2"))
_DEFAULT_RETRY_MAX_DELAY = float(os.environ.get("LAYER4_RETRY_MAX_DELAY", "5.0"))
_DEFAULT_CB_FAILURE_THRESHOLD = int(
    os.environ.get("LAYER4_CB_FAILURE_THRESHOLD", "5")
)
_DEFAULT_CB_RECOVERY_TIMEOUT = float(
    os.environ.get("LAYER4_CB_RECOVERY_TIMEOUT", "60.0")
)

# Statuses emitted by the Layer 4 workflow API (WorkflowStatusValue literal).
_KNOWN_STATUSES = {
    "pending",
    "running",
    "paused",
    "interrupted",
    "completed",
    "failed",
    "cancelled",
}


def _truncate_utf8(text: str, max_chars: int) -> str:
    """Truncate *text* to *max_chars* without splitting multi-byte chars.

    Plain slicing ``text[:400]`` is fine for str (Python counts code points),
    but downstream logs/JSON encoders may re-encode to UTF-8; truncating at a
    code-point boundary keeps the result safe to encode in any codec.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


class Layer4UnavailableError(RuntimeError):
    """Raised when the Layer 4 orchestration dependency is unavailable."""

    def __init__(self, code: str, *, status_code: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class Layer4DependencyError(RuntimeError):
    """Raised when Layer 4 returns a deterministic dependency failure."""

    def __init__(
        self,
        code: str,
        *,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.body = body


class _TransientRequestError(RetryableError):
    """Internal marker: a transient (retryable) Layer 4 request failure.

    Wraps network errors and 502/503/504/429 responses so the retry helper
    can classify them without a custom predicate. These failures also trip
    the circuit breaker; deterministic 4xx failures do neither.
    """

    def __init__(
        self,
        code: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class Layer4OrchestrationClient:
    """Sync client for the Layer 4 ``/v1/workflows`` API.

    Authentication uses the platform service-auth contract: the gateway
    forwards the verified tenant (and user when known) plus the shared
    service secret. Tenant identity is never taken from caller input.

    Resilience: transient failures (502/503/504/429, connect errors) are
    retried with full-jitter exponential backoff and protected by a sync
    circuit breaker so a sustained Layer 4 outage fails closed fast rather
    than queuing traffic. Deterministic 4xx failures surface immediately.
    """

    provider_name = "layer4"

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10.0,
        *,
        breaker: SyncCircuitBreaker | None = None,
        max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
        retry_base_delay: float = _DEFAULT_RETRY_BASE_DELAY,
        retry_max_delay: float = _DEFAULT_RETRY_MAX_DELAY,
        sleep=time.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")
        self.max_attempts = max_attempts
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self._sleep = sleep
        self.breaker = breaker or SyncCircuitBreaker(
            "layer4-orchestration",
            failure_threshold=_DEFAULT_CB_FAILURE_THRESHOLD,
            recovery_timeout=_DEFAULT_CB_RECOVERY_TIMEOUT,
        )

    def _headers(self, tenant_id: str, user_id: str | None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": tenant_id,
            "X-Service-Auth": self.service_secret,
        }
        if user_id:
            headers["X-User-ID"] = user_id
        return inject_trace_headers(headers)

    def _is_transient(self, exc: Exception) -> bool:
        """Return True for failures that should be retried.

        Circuit-open failures are NOT retried (the breaker says stop), even
        though they're wrapped in _TransientRequestError for uniform
        handling — they surface immediately as Layer4UnavailableError.
        """
        if isinstance(exc, _TransientRequestError):
            return exc.code != ERR_LAYER4_CIRCUIT_OPEN
        return False

    def _do_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Single HTTP attempt. Raises _TransientRequestError on retryable failures."""
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(
                    method,
                    url,
                    json=json_body,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise _TransientRequestError(ERR_LAYER4_UNAVAILABLE) from exc

        if response.status_code in TRANSIENT_STATUS_CODES:
            raise _TransientRequestError(
                ERR_LAYER4_UNAVAILABLE, status_code=response.status_code
            )

        if response.status_code >= 400:
            raise Layer4DependencyError(
                ERR_LAYER4_HTTP_ERROR,
                status_code=response.status_code,
                body=_truncate_utf8(response.text, 400),
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise Layer4DependencyError(ERR_LAYER4_INVALID_JSON) from exc

        if not isinstance(body, dict):
            raise Layer4DependencyError(ERR_LAYER4_INVALID_RESPONSE_TYPE)

        return body

    def _request(
        self,
        method: str,
        path: str,
        *,
        tenant_id: str,
        user_id: str | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = self._headers(tenant_id, user_id)
        if extra_headers:
            headers.update(extra_headers)

        def _attempt() -> dict[str, Any]:
            # Each individual attempt goes through the breaker so a
            # sustained outage opens the circuit and subsequent requests
            # fail fast. The retry wraps the breaker so a single transient
            # failure is retried before the breaker counts it as a failure
            # on the final attempt.
            try:
                return self.breaker.call(
                    self._do_request,
                    method,
                    url,
                    headers=headers,
                    json_body=json_body,
                )
            except SyncCircuitBreakerOpen as exc:
                # Translate to a retryable marker so retry_transient can
                # decide whether to keep retrying (it should not — the
                # breaker is open).
                raise _TransientRequestError(
                    ERR_LAYER4_CIRCUIT_OPEN, status_code=None
                ) from exc

        try:
            body = retry_transient(
                _attempt,
                max_attempts=self.max_attempts,
                base_delay=self.retry_base_delay,
                max_delay=self.retry_max_delay,
                retry_on=self._is_transient,
                sleep=self._sleep,
            )
        except _TransientRequestError as exc:
            if exc.code == ERR_LAYER4_CIRCUIT_OPEN:
                raise Layer4UnavailableError(ERR_LAYER4_CIRCUIT_OPEN)
            raise Layer4UnavailableError(
                ERR_LAYER4_UNAVAILABLE, status_code=exc.status_code
            ) from exc
        return body

    def create_workflow(
        self,
        *,
        tenant_id: str,
        workflow_type: str,
        account_id: str | None,
        input_data: dict[str, Any] | None,
        user_id: str | None = None,
        workflow_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        # Generate a stable workflow_id/idempotency_key once across retries
        # to prevent duplicate workflow executions upstream on transient network drops.
        stable_workflow_id = workflow_id or str(uuid.uuid4())
        stable_idempotency_key = idempotency_key or stable_workflow_id
        inputs: dict[str, Any] = {"custom_data": input_data or {}}
        if account_id:
            inputs["prospect_id"] = account_id
        return self._request(
            "POST",
            "/v1/workflows",
            tenant_id=tenant_id,
            user_id=user_id,
            json_body={
                "workflow_type": workflow_type,
                "inputs": inputs,
                "workflow_id": stable_workflow_id,
            },
            extra_headers={
                "Idempotency-Key": stable_idempotency_key,
                "X-Idempotency-Key": stable_idempotency_key,
            },
        )

    def get_workflow(self, *, tenant_id: str, workflow_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/v1/workflows/{workflow_id}", tenant_id=tenant_id
        )

    def get_workflow_result(
        self, *, tenant_id: str, workflow_id: str
    ) -> dict[str, Any]:
        return self._request(
            "GET", f"/v1/workflows/{workflow_id}/result", tenant_id=tenant_id
        )

    def pause_workflow(
        self, *, tenant_id: str, workflow_id: str, user_id: str, reason: str | None = None
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/workflows/{workflow_id}/pause",
            tenant_id=tenant_id,
            user_id=user_id,
            json_body={"user_id": user_id, "reason": reason, "tenant_id": tenant_id},
        )

    def resume_workflow(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        user_id: str,
        resume_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/workflows/{workflow_id}/resume",
            tenant_id=tenant_id,
            user_id=user_id,
            json_body={
                "user_id": user_id,
                "resume_data": resume_data or {},
                "tenant_id": tenant_id,
            },
        )

    def cancel_workflow(self, *, tenant_id: str, workflow_id: str) -> dict[str, Any]:
        return self._request(
            "DELETE", f"/v1/workflows/{workflow_id}", tenant_id=tenant_id
        )


def _map_status(status: Any, *, default: str) -> str:
    value = str(status or "").strip().lower()
    return value if value in _KNOWN_STATUSES else default


class AgentOrchestrator:
    """Gateway-side projection of Layer 4 workflow runs.

    The local ``db.agent_runs`` records are derived from Layer 4 workflow
    state and can be rebuilt from it; they exist so list/SSE responses are
    cheap. All lifecycle operations delegate to Layer 4 first and update
    the projection second.
    """

    def __init__(self, layer4_client: Layer4OrchestrationClient | None = None):
        settings = get_settings()
        self.layer4_client = layer4_client or Layer4OrchestrationClient(
            base_url=settings.layer4_api_base_url,
            timeout_seconds=settings.layer4_timeout_seconds,
        )

    def create_run(
        self,
        tenant_id: str,
        workflow_type: str,
        account_id: str | None = None,
        input_data: Mapping[str, object] | None = None,
        user_id: str | None = None,
    ) -> AgentRun:
        delegated = self.layer4_client.create_workflow(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            account_id=account_id,
            input_data=input_data,
            user_id=user_id,
        )
        workflow_id = str(
            delegated.get("workflow_instance_id")
            or delegated.get("workflow_id")
            or delegated.get("id")
            or ""
        )
        if not workflow_id:
            raise Layer4DependencyError(ERR_LAYER4_INVALID_RESPONSE_TYPE)
        run = AgentRun(
            id=workflow_id,
            tenant_id=tenant_id,
            account_id=account_id,
            workflow_type=workflow_type,
            status=_map_status(delegated.get("status"), default="pending"),
            input=input_data or {},
            output={
                "provider": self.layer4_client.provider_name,
                "projection": "derived-from-layer4-workflow",
                "layer4": delegated,
            },
        )
        db.agent_runs.insert(workflow_id, run)
        return run

    def get_run(self, run_id: str, *, tenant_id: str) -> AgentRun | None:
        """Return the run, refreshing the projection from Layer 4."""
        run = db.agent_runs.get(run_id, tenant_id=tenant_id)
        if not run:
            return None
        try:
            delegated = self.layer4_client.get_workflow(
                tenant_id=tenant_id, workflow_id=run_id
            )
        except Layer4DependencyError as exc:
            if exc.status_code == 404:
                return None
            logger.warning(
                "Layer 4 refresh failed for run %s: status=%s code=%s body=%s",
                run_id,
                exc.status_code,
                exc.code,
                exc.body,
            )
            raise
        except Layer4UnavailableError as exc:
            logger.warning(
                "Layer 4 unavailable for run %s refresh: code=%s status=%s",
                run_id,
                exc.code,
                exc.status_code,
            )
            return run
        self._apply_layer4_state(run, delegated)
        return run

    def pause_run(self, run_id: str, *, tenant_id: str, user_id: str | None = None) -> AgentRun:
        run = db.agent_runs.get(run_id, tenant_id=tenant_id)
        if not run:
            raise ValueError(ERR_RUN_NOT_FOUND)
        delegated = self.layer4_client.pause_workflow(
            tenant_id=tenant_id,
            workflow_id=run_id,
            user_id=user_id or "gateway-user",
        )
        run.status = "paused"
        self._apply_layer4_state(run, delegated, default_status="paused")
        return run

    def resume_run(
        self,
        run_id: str,
        *,
        tenant_id: str,
        user_id: str | None = None,
        resume_data: Mapping[str, object] | None = None,
    ) -> AgentRun:
        run = db.agent_runs.get(run_id, tenant_id=tenant_id)
        if not run:
            raise ValueError(ERR_RUN_NOT_FOUND)
        delegated = self.layer4_client.resume_workflow(
            tenant_id=tenant_id,
            workflow_id=run_id,
            user_id=user_id or "gateway-user",
            resume_data=resume_data,
        )
        self._apply_layer4_state(run, delegated, default_status="running")
        return run

    def cancel_run(self, run_id: str, *, tenant_id: str) -> AgentRun:
        run = db.agent_runs.get(run_id, tenant_id=tenant_id)
        if not run:
            raise ValueError(ERR_RUN_NOT_FOUND)
        delegated = self.layer4_client.cancel_workflow(
            tenant_id=tenant_id, workflow_id=run_id
        )
        self._apply_layer4_state(run, delegated, default_status="cancelled")
        return run

    def _apply_layer4_state(
        self, run: AgentRun, delegated: Mapping[str, object], *, default_status: str | None = None
    ) -> None:
        run.status = _map_status(
            delegated.get("status"), default=default_status or run.status
        )
        run.updated_at = datetime.now(UTC).isoformat()
        run.output = {
            "provider": self.layer4_client.provider_name,
            "projection": "derived-from-layer4-workflow",
            "layer4": delegated,
        }
        db.agent_runs.update(
            run.id,
            tenant_id=run.tenant_id,
            status=run.status,
            output=run.output,
        )


_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


class _LazyOrchestrator:
    _instance: AgentOrchestrator | None = None

    @classmethod
    def _get(cls) -> AgentOrchestrator:
        if cls._instance is None:
            cls._instance = AgentOrchestrator()
        return cls._instance

    def __getattr__(self, name: str):
        return getattr(self._get(), name)

    def __setattr__(self, name: str, value):
        if name == "_instance":
            super().__setattr__(name, value)
        else:
            setattr(self._get(), name, value)

    def __call__(self, *args, **kwargs):
        return self._get()(*args, **kwargs)


orchestrator: AgentOrchestrator = _LazyOrchestrator()  # type: ignore[assignment]
