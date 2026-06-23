"""Shared health probe contract primitives.

This module defines the canonical probe payload used by service-local
adapters to keep legacy route behavior stable while standardizing internals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping

DependencyState = Literal["healthy", "degraded", "unhealthy", "unknown"]

_STATUS_ALIASES: dict[str, str] = {
    "ok": "healthy",
    "up": "healthy",
    "alive": "healthy",
    "failed": "unhealthy",
    "error": "unhealthy",
    "down": "unhealthy",
    "unavailable": "degraded",
}

_READY_STATUSES = {"healthy", "ready"}
_DEPENDENCY_STATUS_ALIASES: dict[str, DependencyState] = {
    "ok": "healthy",
    "ready": "healthy",
    "failed": "unhealthy",
    "error": "unhealthy",
    "not_ready": "unhealthy",
    "unavailable": "unknown",
}


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


def normalize_probe_status(status: Any) -> str:
    """Normalize status values emitted by service-local adapters."""

    raw = str(status or "unknown").strip().lower()
    return _STATUS_ALIASES.get(raw, raw)


def derive_probe_readiness(status: str, readiness: dict[str, Any] | ProbeReadiness | None) -> ProbeReadiness:
    """Return a normalized readiness model for a probe payload."""

    if isinstance(readiness, ProbeReadiness):
        return readiness

    normalized_status = normalize_probe_status(status)
    if readiness is None:
        is_ready = normalized_status in _READY_STATUSES
        reason = "dependencies_available" if is_ready else "dependency_unhealthy"
        return ProbeReadiness(is_ready=is_ready, reason=reason)

    is_ready = readiness.get("is_ready")
    if is_ready is None:
        is_ready = normalized_status in _READY_STATUSES
    reason = str(
        readiness.get("reason")
        or ("dependencies_available" if bool(is_ready) else "dependency_unhealthy")
    )
    return ProbeReadiness(is_ready=bool(is_ready), reason=reason)


def normalize_probe_dependencies(
    dependencies: list[dict[str, Any] | ProbeDependencyStatus] | None,
) -> list[ProbeDependencyStatus]:
    """Normalize dependencies while accepting legacy field aliases."""

    dependency_models: list[ProbeDependencyStatus] = []
    for dep in dependencies or []:
        if isinstance(dep, ProbeDependencyStatus):
            dependency_models.append(dep)
            continue

        if hasattr(dep, "model_dump"):
            dep = dep.model_dump()  # type: ignore[assignment]
        elif not isinstance(dep, dict):
            dep = dict(getattr(dep, "__dict__", {}))

        name = str(dep.get("name", "unknown"))
        raw_status = str(dep.get("status", "unknown")).strip().lower()
        mapped_status = _DEPENDENCY_STATUS_ALIASES.get(raw_status, raw_status)
        if mapped_status not in {"healthy", "degraded", "unhealthy", "unknown"}:
            mapped_status = "unknown"

        failure_reason = dep.get("failure_reason")
        reason = dep.get("reason")
        error = dep.get("error")
        normalized_reason = reason or failure_reason
        normalized_error = error if error is not None else failure_reason

        dependency_models.append(
            ProbeDependencyStatus(
                name=name,
                status=mapped_status,
                required=bool(dep.get("required", True)),
                reason=None if normalized_reason is None else str(normalized_reason),
                error=None if normalized_error is None else str(normalized_error),
            )
        )

    return dependency_models


def normalize_probe_payload(
    *,
    status: str,
    service: str,
    readiness: dict[str, Any] | ProbeReadiness | None = None,
    dependencies: list[dict[str, Any] | ProbeDependencyStatus] | None = None,
    liveness: str = "alive",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical probe payload while accepting legacy adapter inputs."""

    normalized_status = normalize_probe_status(status)
    readiness_model = derive_probe_readiness(normalized_status, readiness)
    dependency_models = normalize_probe_dependencies(dependencies)

    payload = ProbeStatusPayload(
        status=normalized_status,
        service=service,
        liveness=liveness,
        readiness=readiness_model,
        dependencies=dependency_models,
    )
    result = asdict(payload)
    # Backward-compatible alias for clients that still inspect dependency_status.
    result["dependency_status"] = result["dependencies"]
    if extra:
        result.update(extra)
    return result


def normalize_probe_response(
    payload: Mapping[str, Any],
    *,
    default_service: str,
    liveness: str = "alive",
) -> dict[str, Any]:
    """Normalize a service payload dict to the shared probe contract."""

    data = dict(payload)
    extra = {
        key: value
        for key, value in data.items()
        if key not in {"status", "service", "liveness", "readiness", "dependencies", "dependency_status"}
    }
    return normalize_probe_payload(
        status=str(data.get("status", "unknown")),
        service=str(data.get("service", default_service)),
        liveness=str(data.get("liveness", liveness)),
        readiness=data.get("readiness"),
        dependencies=data.get("dependencies") or data.get("dependency_status"),
        extra=extra,
    )
