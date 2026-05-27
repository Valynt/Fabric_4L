"""Shared health probe contract primitives.

This module defines the canonical probe payload used by service-local
adapters to keep legacy route behavior stable while standardizing internals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

DependencyState = Literal["healthy", "degraded", "unhealthy", "unknown"]


@dataclass(frozen=True)
class ProbeDependencyStatus:
    """Dependency status entry for readiness/liveness probes."""

    name: str
    status: DependencyState
    required: bool = True
    reason: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class ProbeReadiness:
    """Readiness gate outcome."""

    is_ready: bool
    reason: str


@dataclass(frozen=True)
class ProbeStatusPayload:
    """Canonical cross-service probe status payload."""

    status: str
    service: str
    liveness: str
    readiness: ProbeReadiness
    dependencies: list[ProbeDependencyStatus]


def normalize_probe_payload(
    *,
    status: str,
    service: str,
    readiness: dict[str, Any] | ProbeReadiness | None = None,
    dependencies: list[dict[str, Any] | ProbeDependencyStatus] | None = None,
    liveness: str = "alive",
) -> dict[str, Any]:
    """Build a canonical probe payload while accepting legacy adapter inputs."""

    readiness_model = (
        readiness
        if isinstance(readiness, ProbeReadiness)
        else ProbeReadiness(**(readiness or {"is_ready": status == "healthy", "reason": "dependencies_available"}))
    )

    dependency_models: list[ProbeDependencyStatus] = []
    for dep in dependencies or []:
        dependency_models.append(dep if isinstance(dep, ProbeDependencyStatus) else ProbeDependencyStatus(**dep))

    payload = ProbeStatusPayload(
        status=status,
        service=service,
        liveness=liveness,
        readiness=readiness_model,
        dependencies=dependency_models,
    )
    result = asdict(payload)
    # Backward-compatible alias for clients that still inspect dependency_status.
    result["dependency_status"] = result["dependencies"]
    return result
