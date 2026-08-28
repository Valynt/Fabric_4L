"""Auth Plane Telemetry & Observability for Clerk and Internal Envelopes.

Provides Prometheus metrics, structured telemetry helpers, and real-time
SLO / health reporting for the Fabric_4L authentication plane.
"""

from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Any, Literal

from prometheus_client import Counter, Histogram

from app.core.metrics import registry

logger = logging.getLogger(__name__)

# Prometheus metrics registered to the central API registry
AUTH_VERIFICATIONS_TOTAL = Counter(
    "fabric_auth_verifications_total",
    "Total authentication token verifications by provider, outcome, and reason.",
    ("provider", "outcome", "reason"),
    registry=registry,
)

AUTH_VERIFICATION_LATENCY_SECONDS = Histogram(
    "fabric_auth_verification_duration_seconds",
    "Latency of authentication token verification and envelope generation.",
    ("provider", "outcome"),
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
    registry=registry,
)

AUTH_WEBHOOK_EVENTS_TOTAL = Counter(
    "fabric_auth_webhook_events_total",
    "Total Clerk webhook events processed by event type and outcome status.",
    ("event_type", "status"),
    registry=registry,
)

AUTH_WEBHOOK_LATENCY_SECONDS = Histogram(
    "fabric_auth_webhook_duration_seconds",
    "Processing duration of Clerk webhooks in seconds.",
    ("event_type",),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    registry=registry,
)

AUTH_WEBHOOK_REPLAYS_TOTAL = Counter(
    "fabric_auth_webhook_replays_total",
    "Total idempotent duplicate webhook events ignored.",
    ("event_type",),
    registry=registry,
)

AUTH_DLQ_EVENTS_TOTAL = Counter(
    "fabric_auth_webhook_dlq_total",
    "Total webhook events routed to the dead-letter queue by reason.",
    ("event_type", "reason"),
    registry=registry,
)

AUTH_CLOCK_SKEW_SECONDS = Histogram(
    "fabric_auth_clock_skew_seconds",
    "Observed absolute clock skew between token iat and gateway system time.",
    ("provider",),
    buckets=(0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
    registry=registry,
)


class _RollingWindowStats:
    """Thread-safe rolling window statistics collector for real-time SLO metrics."""

    def __init__(self, max_samples: int = 1000) -> None:
        self._lock = threading.Lock()
        self._samples: collections.deque[tuple[float, bool, float, str]] = collections.deque(
            maxlen=max_samples
        )
        self._total_verifications: int = 0
        self._success_count: int = 0
        self._unresolved_tenant_count: int = 0
        self._expired_count: int = 0
        self._start_time: float = time.time()

    def record(self, success: bool, latency: float, reason: str) -> None:
        now = time.time()
        with self._lock:
            self._total_verifications += 1
            if success:
                self._success_count += 1
            if reason == "tenant_unresolved":
                self._unresolved_tenant_count += 1
            elif reason == "expired":
                self._expired_count += 1
            self._samples.append((now, success, latency, reason))

    def get_summary(self) -> dict[str, Any]:
        with self._lock:
            total = self._total_verifications
            success = self._success_count
            unresolved = self._unresolved_tenant_count
            expired = self._expired_count
            latencies = [s[2] for s in self._samples]

        success_rate = (success / total * 100.0) if total > 0 else 100.0
        unresolved_rate = (unresolved / total * 100.0) if total > 0 else 0.0
        expired_rate = (expired / total * 100.0) if total > 0 else 0.0

        if latencies:
            sorted_lat = sorted(latencies)
            p50_idx = int(len(sorted_lat) * 0.50)
            p95_idx = int(len(sorted_lat) * 0.95)
            p99_idx = int(len(sorted_lat) * 0.99)
            p50_ms = sorted_lat[min(p50_idx, len(sorted_lat) - 1)] * 1000.0
            p95_ms = sorted_lat[min(p95_idx, len(sorted_lat) - 1)] * 1000.0
            p99_ms = sorted_lat[min(p99_idx, len(sorted_lat) - 1)] * 1000.0
        else:
            p50_ms = 0.0
            p95_ms = 0.0
            p99_ms = 0.0

        return {
            "total_verifications": total,
            "success_count": success,
            "success_rate_percent": round(success_rate, 2),
            "unresolved_tenant_count": unresolved,
            "unresolved_tenant_rate_percent": round(unresolved_rate, 2),
            "expired_count": expired,
            "expired_rate_percent": round(expired_rate, 2),
            "p50_latency_ms": round(p50_ms, 3),
            "p95_latency_ms": round(p95_ms, 3),
            "p99_latency_ms": round(p99_ms, 3),
            "uptime_seconds": int(time.time() - self._start_time),
        }

    def reset(self) -> None:
        with self._lock:
            self._samples.clear()
            self._total_verifications = 0
            self._success_count = 0
            self._unresolved_tenant_count = 0
            self._expired_count = 0
            self._start_time = time.time()


_stats = _RollingWindowStats()


def record_auth_success(
    provider: str = "clerk",
    tenant_id: str | None = None,
    latency_seconds: float = 0.0,
) -> None:
    """Record a successful authentication event."""
    AUTH_VERIFICATIONS_TOTAL.labels(provider=provider, outcome="success", reason="ok").inc()
    AUTH_VERIFICATION_LATENCY_SECONDS.labels(provider=provider, outcome="success").observe(
        latency_seconds
    )
    _stats.record(success=True, latency=latency_seconds, reason="ok")


def record_auth_failure(
    provider: str = "clerk",
    reason: Literal[
        "expired",
        "azp_mismatch",
        "token_invalid",
        "token_missing",
        "tenant_unresolved",
        "membership_inactive",
        "user_not_provisioned",
        "envelope_misconfigured",
        "clock_skew",
        "internal_error",
    ] = "token_invalid",
    latency_seconds: float = 0.0,
) -> None:
    """Record an authentication failure event."""
    AUTH_VERIFICATIONS_TOTAL.labels(provider=provider, outcome="failure", reason=reason).inc()
    AUTH_VERIFICATION_LATENCY_SECONDS.labels(provider=provider, outcome="failure").observe(
        latency_seconds
    )
    _stats.record(success=False, latency=latency_seconds, reason=reason)


def record_webhook_event(
    event_type: str,
    status: str = "success",
    latency_seconds: float = 0.0,
) -> None:
    """Record a Clerk webhook event execution."""
    AUTH_WEBHOOK_EVENTS_TOTAL.labels(event_type=event_type, status=status).inc()
    AUTH_WEBHOOK_LATENCY_SECONDS.labels(event_type=event_type).observe(latency_seconds)


def record_webhook_replay(event_type: str) -> None:
    """Record a duplicate webhook event ignored due to idempotency."""
    AUTH_WEBHOOK_REPLAYS_TOTAL.labels(event_type=event_type).inc()


def record_webhook_dlq(event_type: str, reason: str) -> None:
    """Record an unprocessable webhook sent to the dead-letter queue."""
    AUTH_DLQ_EVENTS_TOTAL.labels(event_type=event_type, reason=reason).inc()


def record_clock_skew(provider: str, skew_seconds: float) -> None:
    """Record observed clock skew."""
    AUTH_CLOCK_SKEW_SECONDS.labels(provider=provider).observe(abs(skew_seconds))


def get_auth_health_summary() -> dict[str, Any]:
    """Compute and return the real-time Auth Health summary."""
    from app.core.clerk_config import get_auth_settings

    settings = get_auth_settings()
    provider = settings.provider

    # Check JWKS status if Clerk is active
    jwks_status = "unconfigured"
    keys_cached_count = 0
    if settings.clerk is not None:
        try:
            from app.core.clerk_auth import _get_verifier

            verifier = _get_verifier()
            if verifier and verifier.jwks_cache:
                cache_status = verifier.jwks_cache.get_status()
                jwks_status = cache_status["status"]
                keys_cached_count = cache_status["cached_keys_count"]
        except Exception:
            jwks_status = "unreachable"

    # Check Ed25519 signing key status
    envelope_configured = settings.envelope is not None
    active_signing_kid = (
        settings.envelope.signing_key.kid
        if settings.envelope and settings.envelope.signing_key is not None
        else None
    )

    stats_summary = _stats.get_summary()

    # Determine overall status
    is_healthy = True
    issues = []

    if provider == "clerk":
        if not envelope_configured:
            is_healthy = False
            issues.append("internal_envelope_not_configured")
        if stats_summary["total_verifications"] > 20 and stats_summary["success_rate_percent"] < 90.0:
            is_healthy = False
            issues.append("high_verification_failure_rate")

    health_status = "healthy" if is_healthy else ("degraded" if issues else "unhealthy")

    return {
        "status": health_status,
        "provider": provider,
        "clerk_jwks": {
            "status": jwks_status,
            "cached_keys_count": keys_cached_count,
        },
        "internal_envelope": {
            "configured": envelope_configured,
            "active_signing_kid": active_signing_kid,
        },
        "slo_metrics": stats_summary,
        "issues": issues,
    }


def reset_auth_telemetry_stats() -> None:
    """Reset rolling stats (used primarily in test suites)."""
    _stats.reset()
