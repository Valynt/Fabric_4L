from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.database import db
from app.models.schemas import AgentRun, ToolResult


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
    provider_name = "layer4"

    def __init__(self, base_url: str, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def execute_step(self, *, tenant_id: str, run_id: str, step_name: str, tool_name: str | None) -> dict[str, Any]:
        payload = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "step_name": step_name,
            "tool_name": tool_name,
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/internal/orchestrator/execute-step", json=payload)
        except httpx.HTTPError as exc:
            raise Layer4UnavailableError("layer4_unavailable") from exc

        if response.status_code in {502, 503, 504}:
            raise Layer4UnavailableError("layer4_unavailable", status_code=response.status_code)

        if response.status_code >= 400:
            raise Layer4DependencyError(
                "layer4_http_error",
                status_code=response.status_code,
                body=response.text[:400],
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise Layer4DependencyError("layer4_invalid_json") from exc

        if not isinstance(body, dict):
            raise Layer4DependencyError("layer4_invalid_response_type")

        return body


class AgentOrchestrator:
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
    ) -> AgentRun:
        run_id = f"run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{tenant_id[:4]}"
        run = AgentRun(
            id=run_id,
            tenant_id=tenant_id,
            account_id=account_id,
            workflow_type=workflow_type,
            status="pending",
            input=input_data or {},
        )
        db.agent_runs.insert(run_id, run)
        return run

    def execute_step(
        self,
        run_id: str,
        step_name: str,
        tool_name: str | None = None,
        *,
        tenant_id: str,
    ) -> AgentRun:
        run = db.agent_runs.get(run_id, tenant_id=tenant_id)
        if not run:
            raise ValueError("run_not_found")

        run.status = "running"
        run.current_step = step_name
        run.updated_at = datetime.now(UTC).isoformat()

        delegated = self.layer4_client.execute_step(
            tenant_id=run.tenant_id,
            run_id=run_id,
            step_name=step_name,
            tool_name=tool_name,
        )

        if tool_name:
            tool_result = ToolResult(
                id=f"tr-{run_id}-{step_name}",
                agent_run_id=run_id,
                tool_name=tool_name,
                status="success",
                output={"provider": self.layer4_client.provider_name, "step": step_name, "layer4": delegated},
                completed_at=datetime.now(UTC).isoformat(),
            )
            db.tool_results.insert(tool_result.id, tool_result)
            run.tool_results.append(tool_result)

        run.status = "completed"
        run.output = {
            "completed_step": step_name,
            "provider": self.layer4_client.provider_name,
            "layer4": delegated,
        }
        db.agent_runs.update(
            run_id,
            tenant_id=tenant_id,
            status=run.status,
            current_step=run.current_step,
            output=run.output,
            tool_results=run.tool_results,
        )
        return run

    def resume_run(self, run_id: str) -> AgentRun:
        run = db.agent_runs.get(run_id)
        if not run:
            raise ValueError("run_not_found")
        if run.status == "paused":
            run.status = "running"
            run.updated_at = datetime.now(UTC).isoformat()
            db.agent_runs.update(run_id, status=run.status)
        return run

    def cancel_run(self, run_id: str) -> AgentRun:
        run = db.agent_runs.get(run_id)
        if not run:
            raise ValueError("run_not_found")
        run.status = "cancelled"
        run.updated_at = datetime.now(UTC).isoformat()
        db.agent_runs.update(run_id, status=run.status)
        return run


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
