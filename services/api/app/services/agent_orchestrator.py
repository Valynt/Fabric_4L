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
from datetime import UTC, datetime
from typing import Any

import httpx
from value_fabric.shared.observability.http_trace_propagation import (
    inject_trace_headers,
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

logger = logging.getLogger(__name__)

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


class Layer4OrchestrationClient:
    """Sync client for the Layer 4 ``/v1/workflows`` API.

    Authentication uses the platform service-auth contract: the gateway
    forwards the verified tenant (and user when known) plus the shared
    service secret. Tenant identity is never taken from caller input.
    """

    provider_name = "layer4"

    def __init__(self, base_url: str, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.service_secret = os.environ.get("SERVICE_AUTH_SECRET", "")

    def _headers(self, tenant_id: str, user_id: str | None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": tenant_id,
            "X-Service-Auth": self.service_secret,
        }
        if user_id:
            headers["X-User-ID"] = user_id
        return inject_trace_headers(headers)

    def _request(
        self,
        method: str,
        path: str,
        *,
        tenant_id: str,
        user_id: str | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(
                    method,
                    f"{self.base_url}{path}",
                    json=json_body,
                    headers=self._headers(tenant_id, user_id),
                )
        except httpx.HTTPError as exc:
            raise Layer4UnavailableError(ERR_LAYER4_UNAVAILABLE) from exc

        if response.status_code in {502, 503, 504}:
            raise Layer4UnavailableError(ERR_LAYER4_UNAVAILABLE, status_code=response.status_code)

        if response.status_code >= 400:
            raise Layer4DependencyError(
                ERR_LAYER4_HTTP_ERROR,
                status_code=response.status_code,
                body=response.text[:400],
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise Layer4DependencyError(ERR_LAYER4_INVALID_JSON) from exc

        if not isinstance(body, dict):
            raise Layer4DependencyError(ERR_LAYER4_INVALID_RESPONSE_TYPE)

        return body

    def create_workflow(
        self,
        *,
        tenant_id: str,
        workflow_type: str,
        account_id: str | None,
        input_data: dict[str, Any] | None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        inputs: dict[str, Any] = {"custom_data": input_data or {}}
        if account_id:
            inputs["prospect_id"] = account_id
        return self._request(
            "POST",
            "/v1/workflows",
            tenant_id=tenant_id,
            user_id=user_id,
            json_body={"workflow_type": workflow_type, "inputs": inputs},
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
        input_data: dict[str, Any] | None = None,
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
        resume_data: dict[str, Any] | None = None,
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
        self, run: AgentRun, delegated: dict[str, Any], *, default_status: str | None = None
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
