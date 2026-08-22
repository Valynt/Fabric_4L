"""Pluggable health/readiness probe contracts and aggregation.

This module is intentionally framework-agnostic in its core logic. Probes are
small async callables that return a :class:`ProbeResult`. The aggregator
applies a per-probe timeout, caches the readiness result for a configurable
window, and never raises out of the request path.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol, runtime_checkable


import logging


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of a single readiness probe."""

    name: str
    healthy: bool
    detail: str | None = None
    latency_ms: float | None = None


@runtime_checkable
class HealthCheckProbe(Protocol):
    """Pluggable readiness probe.

    Implementations must be safe to call concurrently and must not raise; any
    failure must be reported via :class:`ProbeResult` with ``healthy=False``.
    """

    name: str

    async def check(self) -> ProbeResult: ...  # pragma: no cover - protocol


ProbeCallable = Callable[[], Awaitable[ProbeResult]]


@dataclass(frozen=True)
class CallableProbe:
    """Adapter that turns an async callable into a :class:`HealthCheckProbe`."""

    name: str
    fn: ProbeCallable

    async def check(self) -> ProbeResult:
        try:
            return await self.fn()
        except Exception as exc:  # noqa: BLE001 - probes must never raise
            logger.warning("Callable probe %s failed: %s", self.name, exc)
            return ProbeResult(name=self.name, healthy=False, detail="probe_failed")


@dataclass(frozen=True)
class RedisHealthProbe:
    """Health probe for Redis using duck-typed client (sync or async)."""

    _client: object = field(repr=False)
    name: str = "redis"

    async def check(self) -> ProbeResult:
        client = self._client
        if client is None:
            return ProbeResult(name=self.name, healthy=False, detail="client_not_configured")
        try:
            ping = getattr(client, "ping", None)
            if ping is None:
                return ProbeResult(name=self.name, healthy=False, detail="client_has_no_ping")
            if asyncio.iscoroutinefunction(ping):
                await ping()
            else:
                await asyncio.to_thread(ping)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis health probe %s failed: %s", self.name, exc)
            return ProbeResult(name=self.name, healthy=False, detail="probe_failed")
        return ProbeResult(name=self.name, healthy=True)


async def _run_probe_with_timeout(probe: HealthCheckProbe, timeout_seconds: float) -> ProbeResult:
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(probe.check(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return ProbeResult(
            name=getattr(probe, "name", probe.__class__.__name__),
            healthy=False,
            detail=f"timeout_after_{timeout_seconds:.1f}s",
            latency_ms=(time.perf_counter() - start) * 1000.0,
        )
    except Exception as exc:  # noqa: BLE001 - never propagate
        probe_name = getattr(probe, "name", probe.__class__.__name__)
        logger.warning("Health probe %s raised unexpected exception: %s", probe_name, exc)
        return ProbeResult(
            name=probe_name,
            healthy=False,
            detail="probe_failed",
            latency_ms=(time.perf_counter() - start) * 1000.0,
        )
    latency_ms = (time.perf_counter() - start) * 1000.0
    if result.latency_ms is None:
        return ProbeResult(
            name=result.name,
            healthy=result.healthy,
            detail=result.detail,
            latency_ms=latency_ms,
        )
    return result


async def aggregate_probes(
    probes: list[HealthCheckProbe],
    *,
    timeout_seconds: float = 2.0,
) -> tuple[bool, list[ProbeResult]]:
    """Run every probe concurrently within ``timeout_seconds`` each."""

    if not probes:
        return True, []
    results = await asyncio.gather(
        *[_run_probe_with_timeout(p, timeout_seconds) for p in probes]
    )
    overall = all(r.healthy for r in results)
    return overall, list(results)


def build_readiness_payload(
    *,
    service_name: str,
    healthy: bool,
    probe_results: list[ProbeResult],
    version: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "service": service_name,
        "status": "ready" if healthy else "not_ready",
        "probes": [
            {
                "name": r.name,
                "healthy": r.healthy,
                "detail": r.detail,
                "latency_ms": r.latency_ms,
            }
            for r in probe_results
        ],
    }
    if version is not None:
        payload["version"] = version
    return payload
