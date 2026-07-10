"""Circuit breaker framework for Fabric_4L cross-service resilience.

This module provides circuit breaker patterns for all cross-service calls
in the Fabric_4L 6-layer architecture. Each breaker:

1. Tracks failure/success counts
2. Transitions between CLOSED -> OPEN -> HALF_OPEN -> CLOSED
3. Emits Prometheus metrics for all state transitions
4. Integrates with OpenTelemetry for distributed tracing
5. Provides fallback behavior per critical dependency

Dependencies:
    - circuitbreaker >= 1.4.0
    - prometheus_client >= 0.17.0
    - opentelemetry-api >= 1.20.0
    - structlog >= 23.0.0

Usage:
    from value_fabric.shared.resilience import (
        CircuitState, ServiceCircuitBreaker,
        call_layer3_search, call_neo4j_query, call_redis_get,
        get_breaker_metrics, BreakerConfig,
    )

    # Direct breaker usage
    breaker = ServiceCircuitBreaker("neo4j", BreakerConfig.NEO4J)
    result = await breaker.call(_execute_cypher, "MATCH (n) RETURN n")

Reference:
    - https://martinfowler.com/bliki/CircuitBreaker.html
    - https://docs.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
)

import structlog
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("fabric4l.resilience")

# ---------------------------------------------------------------------------
# Prometheus Metrics — all state transitions are instrumented
# ---------------------------------------------------------------------------

# Gauge: current state of each breaker (0=closed, 1=open, 2=half_open)
CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Current state of the circuit breaker",
    ["service", "layer"],
)

# Counter: total failures by service
CIRCUIT_BREAKER_FAILURES = Counter(
    "circuit_breaker_failures_total",
    "Total number of failures seen by the circuit breaker",
    ["service", "layer", "exception_type"],
)

# Counter: total successes by service
CIRCUIT_BREAKER_SUCCESSES = Counter(
    "circuit_breaker_successes_total",
    "Total number of successes seen by the circuit breaker",
    ["service", "layer"],
)

# Counter: state transitions
CIRCUIT_BREAKER_TRANSITIONS = Counter(
    "circuit_breaker_transitions_total",
    "Total number of state transitions",
    ["service", "layer", "from_state", "to_state"],
)

# Histogram: call duration through breaker
CIRCUIT_BREAKER_DURATION = Histogram(
    "circuit_breaker_call_duration_seconds",
    "Duration of calls through the circuit breaker",
    ["service", "layer", "result"],  # result = success | failure | short_circuit
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Gauge: consecutive failure count
CIRCUIT_BREAKER_CONSECUTIVE_FAILURES = Gauge(
    "circuit_breaker_consecutive_failures",
    "Current consecutive failure count",
    ["service", "layer"],
)

# Counter: fallback invocations
CIRCUIT_BREAKER_FALLBACKS = Counter(
    "circuit_breaker_fallbacks_total",
    "Total number of fallback invocations",
    ["service", "layer", "fallback_type"],
)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    """Circuit breaker states.

    CLOSED    — Normal operation, requests pass through.
    OPEN      — Failure threshold exceeded, requests short-circuited.
    HALF_OPEN — Trial period after recovery timeout, testing if service healed.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def _metric_value(self) -> int:
        return {CircuitState.CLOSED: 0, CircuitState.OPEN: 1, CircuitState.HALF_OPEN: 2}[self]


class ServiceUnavailable(Exception):
    """Raised when a downstream service is unavailable.

    This is the primary exception type monitored by circuit breakers.
    Other exceptions can be registered per-breaker config.
    """

    pass


class CircuitBreakerOpen(Exception):
    """Raised when a call is rejected because the circuit breaker is OPEN.

    Carries metadata about the breaker state for debugging.
    """

    def __init__(
        self,
        service: str,
        state: CircuitState,
        consecutive_failures: int,
        open_until: float | None = None,
    ) -> None:
        self.service = service
        self.state = state
        self.consecutive_failures = consecutive_failures
        self.open_until = open_until
        super().__init__(
            f"Circuit breaker for '{service}' is {state.value} "
            f"({consecutive_failures} consecutive failures)"
        )


@dataclass(frozen=True)
class BreakerConfig:
    """Immutable configuration for a circuit breaker.

    Each service has tuned parameters based on its criticality and
    observed failure patterns.
    """

    failure_threshold: int = 5
    recovery_timeout_sec: float = 30.0
    half_open_max_calls: int = 3
    success_threshold_half_open: int = 2
    expected_exceptions: tuple[type[Exception], ...] = (ServiceUnavailable,)
    layer: str = "unknown"
    fallback_enabled: bool = True

    # --- Predefined configs per service ---

    NEO4J: Callable[[], "BreakerConfig"] = lambda: BreakerConfig(
        failure_threshold=5,
        recovery_timeout_sec=30.0,
        half_open_max_calls=3,
        success_threshold_half_open=2,
        expected_exceptions=(ServiceUnavailable, ConnectionError, TimeoutError),
        layer="l3",
        fallback_enabled=True,
    )

    POSTGRES: Callable[[], "BreakerConfig"] = lambda: BreakerConfig(
        failure_threshold=8,
        recovery_timeout_sec=60.0,
        half_open_max_calls=5,
        success_threshold_half_open=3,
        expected_exceptions=(ServiceUnavailable, ConnectionError, TimeoutError),
        layer="l3",
        fallback_enabled=False,  # No fallback for primary DB — fail fast
    )

    REDIS: Callable[[], "BreakerConfig"] = lambda: BreakerConfig(
        failure_threshold=5,
        recovery_timeout_sec=15.0,  # Faster recovery — cache is non-critical
        half_open_max_calls=2,
        success_threshold_half_open=1,
        expected_exceptions=(ServiceUnavailable, ConnectionError, TimeoutError),
        layer="shared",
        fallback_enabled=True,
    )

    L4_AGENT: Callable[[], "BreakerConfig"] = lambda: BreakerConfig(
        failure_threshold=5,
        recovery_timeout_sec=30.0,
        half_open_max_calls=3,
        success_threshold_half_open=2,
        expected_exceptions=(ServiceUnavailable, ConnectionError, TimeoutError),
        layer="l4",
        fallback_enabled=True,
    )

    L1_INGESTION: Callable[[], "BreakerConfig"] = lambda: BreakerConfig(
        failure_threshold=10,
        recovery_timeout_sec=60.0,
        half_open_max_calls=5,
        success_threshold_half_open=3,
        expected_exceptions=(ServiceUnavailable,),
        layer="l1",
        fallback_enabled=False,  # Ingestion must succeed or fail explicitly
    )

    L2_EXTRACTION: Callable[[], "BreakerConfig"] = lambda: BreakerConfig(
        failure_threshold=8,
        recovery_timeout_sec=45.0,
        half_open_max_calls=4,
        success_threshold_half_open=2,
        expected_exceptions=(ServiceUnavailable,),
        layer="l2",
        fallback_enabled=True,
    )


@dataclass
class BreakerSnapshot:
    """Read-only snapshot of breaker state for health/debug endpoints."""

    service: str
    state: CircuitState
    consecutive_failures: int
    success_count: int
    failure_count: int
    fallback_count: int
    last_failure_time: float | None
    opened_at: float | None
    config: BreakerConfig


# ---------------------------------------------------------------------------
# Core Circuit Breaker Implementation
# ---------------------------------------------------------------------------

P = ParamSpec("P")
T = TypeVar("T")


class ServiceCircuitBreaker(Generic[P, T]):
    """Production-grade circuit breaker with full metrics and tracing.

    Example:
        breaker = ServiceCircuitBreaker("neo4j", BreakerConfig.NEO4J())

        async def query_graph(cypher: str) -> dict:
            # ... actual Neo4j call ...
            pass

        result = await breaker.call(query_graph, "MATCH (n) RETURN n")
    """

    _registry: dict[str, "ServiceCircuitBreaker"] = {}

    def __init__(self, service: str, config: BreakerConfig | None = None) -> None:
        self.service = service
        self.config = config or BreakerConfig()
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._success_count = 0
        self._failure_count = 0
        self._fallback_count = 0
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._last_failure_time: float | None = None
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

        # Register in global registry
        ServiceCircuitBreaker._registry[service] = self

        # Initialize Prometheus gauge
        CIRCUIT_BREAKER_STATE.labels(service=service, layer=self.config.layer).set(0)

        logger.info(
            "circuit_breaker.initialized",
            service=service,
            layer=self.config.layer,
            failure_threshold=self.config.failure_threshold,
            recovery_timeout=self.config.recovery_timeout_sec,
        )

    # --- Public API ---

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def snapshot(self) -> BreakerSnapshot:
        return BreakerSnapshot(
            service=self.service,
            state=self._state,
            consecutive_failures=self._consecutive_failures,
            success_count=self._success_count,
            failure_count=self._failure_count,
            fallback_count=self._fallback_count,
            last_failure_time=self._last_failure_time,
            opened_at=self._opened_at,
            config=self.config,
        )

    async def call(
        self,
        fn: Callable[P, Awaitable[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        """Execute fn through the circuit breaker with full instrumentation."""
        with tracer.start_as_current_span(
            f"circuit_breaker.{self.service}",
            kind=SpanKind.INTERNAL,
            attributes={
                "circuit_breaker.service": self.service,
                "circuit_breaker.layer": self.config.layer,
                "circuit_breaker.state": self._state.value,
            },
        ) as span:
            # Check if we should short-circuit
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    async with self._lock:
                        if self._state == CircuitState.OPEN and self._should_attempt_reset():
                            self._transition_to(CircuitState.HALF_OPEN)
                            self._half_open_calls = 0
                            self._half_open_successes = 0
                else:
                    # Still OPEN — short circuit
                    span.set_attribute("circuit_breaker.short_circuited", True)
                    CIRCUIT_BREAKER_DURATION.labels(
                        service=self.service,
                        layer=self.config.layer,
                        result="short_circuit",
                    ).observe(0.0)
                    raise CircuitBreakerOpen(
                        self.service,
                        self._state,
                        self._consecutive_failures,
                        open_until=self._opened_at + self.config.recovery_timeout_sec if self._opened_at else None,
                    )

            # HALF_OPEN: limit trial calls
            if self._state == CircuitState.HALF_OPEN:
                async with self._lock:
                    if self._half_open_calls >= self.config.half_open_max_calls:
                        raise CircuitBreakerOpen(
                            self.service,
                            self._state,
                            self._consecutive_failures,
                        )
                    self._half_open_calls += 1

            # Execute the call
            start = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                await self._on_success()
                duration = time.perf_counter() - start
                CIRCUIT_BREAKER_DURATION.labels(
                    service=self.service,
                    layer=self.config.layer,
                    result="success",
                ).observe(duration)
                span.set_attribute("circuit_breaker.result", "success")
                span.set_status(Status(StatusCode.OK))
                return result

            except Exception as exc:
                duration = time.perf_counter() - start
                should_count = any(isinstance(exc, exc_type) for exc_type in self.config.expected_exceptions)

                if should_count:
                    await self._on_failure(exc)
                    CIRCUIT_BREAKER_DURATION.labels(
                        service=self.service,
                        layer=self.config.layer,
                        result="failure",
                    ).observe(duration)
                    span.set_attribute("circuit_breaker.result", "failure")
                    span.set_attribute("error.type", type(exc).__name__)
                    span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                else:
                    # Unexpected exception — don't count toward breaker
                    span.set_attribute("circuit_breaker.result", "unexpected_error")
                    span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                raise

    # --- State machine ---

    async def _on_success(self) -> None:
        async with self._lock:
            self._success_count += 1
            CIRCUIT_BREAKER_SUCCESSES.labels(
                service=self.service, layer=self.config.layer
            ).inc()
            CIRCUIT_BREAKER_CONSECUTIVE_FAILURES.labels(
                service=self.service, layer=self.config.layer
            ).set(0)

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.config.success_threshold_half_open:
                    self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                self._consecutive_failures = 0

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._failure_count += 1
            self._consecutive_failures += 1
            self._last_failure_time = time.time()

            CIRCUIT_BREAKER_FAILURES.labels(
                service=self.service,
                layer=self.config.layer,
                exception_type=type(exc).__name__,
            ).inc()
            CIRCUIT_BREAKER_CONSECUTIVE_FAILURES.labels(
                service=self.service, layer=self.config.layer
            ).set(self._consecutive_failures)

            if self._state == CircuitState.HALF_OPEN:
                # Failed in HALF_OPEN — go back to OPEN immediately
                self._transition_to(CircuitState.OPEN)
            elif self._consecutive_failures >= self.config.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        CIRCUIT_BREAKER_STATE.labels(
            service=self.service, layer=self.config.layer
        ).set(new_state._metric_value())
        CIRCUIT_BREAKER_TRANSITIONS.labels(
            service=self.service,
            layer=self.config.layer,
            from_state=old_state.value,
            to_state=new_state.value,
        ).inc()

        if new_state == CircuitState.OPEN:
            self._opened_at = time.time()
            logger.warning(
                "circuit_breaker.opened",
                service=self.service,
                consecutive_failures=self._consecutive_failures,
                recovery_timeout=self.config.recovery_timeout_sec,
            )
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._opened_at = None
            logger.info(
                "circuit_breaker.closed",
                service=self.service,
                success_count=self._success_count,
            )
        elif new_state == CircuitState.HALF_OPEN:
            logger.info(
                "circuit_breaker.half_open",
                service=self.service,
                max_calls=self.config.half_open_max_calls,
            )

    def _should_attempt_reset(self) -> bool:
        if self._opened_at is None:
            return True
        return (time.time() - self._opened_at) >= self.config.recovery_timeout_sec

    # --- Registry ---

    @classmethod
    def get_breaker(cls, service: str) -> "ServiceCircuitBreaker | None":
        return cls._registry.get(service)

    @classmethod
    def get_all_snapshots(cls) -> dict[str, BreakerSnapshot]:
        return {name: breaker.snapshot for name, breaker in cls._registry.items()}

    @classmethod
    def reset_all(cls) -> None:
        """Reset all breakers to CLOSED. Useful after drills or incidents."""
        for breaker in cls._registry.values():
            breaker._state = CircuitState.CLOSED
            breaker._consecutive_failures = 0
            breaker._half_open_calls = 0
            breaker._half_open_successes = 0
            breaker._opened_at = None
            CIRCUIT_BREAKER_STATE.labels(
                service=breaker.service, layer=breaker.config.layer
            ).set(0)
            CIRCUIT_BREAKER_CONSECUTIVE_FAILURES.labels(
                service=breaker.service, layer=breaker.config.layer
            ).set(0)
        logger.info("circuit_breaker.all_reset")


# ---------------------------------------------------------------------------
# Decorator for easy function wrapping
# ---------------------------------------------------------------------------

def circuit_breaker(
    service: str,
    config: BreakerConfig | None = None,
    fallback: Callable[..., Awaitable[Any]] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator to wrap an async function with a circuit breaker.

    Example:
        @circuit_breaker("neo4j", BreakerConfig.NEO4J(), fallback=pgvector_fallback)
        async def query_neo4j(cypher: str) -> dict:
            ...
    """
    breaker = ServiceCircuitBreaker(service, config)

    def decorator(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await breaker.call(fn, *args, **kwargs)
            except CircuitBreakerOpen:
                if fallback and breaker.config.fallback_enabled:
                    CIRCUIT_BREAKER_FALLBACKS.labels(
                        service=service,
                        layer=breaker.config.layer,
                        fallback_type=fallback.__name__,
                    ).inc()
                    breaker._fallback_count += 1
                    logger.info(
                        "circuit_breaker.fallback_executed",
                        service=service,
                        fallback=fallback.__name__,
                    )
                    return await fallback(*args, **kwargs)
                raise

        # Attach breaker for introspection
        wrapper._circuit_breaker = breaker  # type: ignore[attr-defined]
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Pre-configured breakers for each cross-service call
# ---------------------------------------------------------------------------

# Neo4j breaker (L3 Knowledge Graph)
_neo4j_breaker = ServiceCircuitBreaker("neo4j", BreakerConfig.NEO4J())

# PostgreSQL breaker
_postgres_breaker = ServiceCircuitBreaker("postgres", BreakerConfig.POSTGRES())

# Redis breaker
_redis_breaker = ServiceCircuitBreaker("redis", BreakerConfig.REDIS())

# Layer 4 Agent breaker
_l4_agent_breaker = ServiceCircuitBreaker("l4_agent", BreakerConfig.L4_AGENT())

# Layer 2 Extraction breaker
_l2_extraction_breaker = ServiceCircuitBreaker("l2_extraction", BreakerConfig.L2_EXTRACTION())


# ---------------------------------------------------------------------------
# Service-specific wrapped functions with fallbacks
# ---------------------------------------------------------------------------

async def call_neo4j_query(cypher: str, tenant_id: str, **params: Any) -> list[dict[str, Any]]:
    """Execute a Cypher query against Neo4j with circuit breaker.

    Fallback: pgvector similarity search in PostgreSQL.
    """
    async def _execute() -> list[dict[str, Any]]:
        from neo4j import AsyncGraphDatabase  # type: ignore[import-untyped]

        uri = _get_neo4j_uri()
        auth = _get_neo4j_auth()
        driver = AsyncGraphDatabase.driver(uri, auth=auth)
        try:
            async with driver.session() as session:
                result = await session.run(cypher, tenant_id=tenant_id, **params)
                records = await result.data()
                return records
        finally:
            await driver.close()

    async def _pgvector_fallback(cypher: str, tenant_id: str, **params: Any) -> list[dict[str, Any]]:
        """Fallback to pgvector similarity search when Neo4j is unavailable."""
        logger.info("fallback.pgvector_activated", tenant_id=tenant_id, original_query=cypher[:100])
        CIRCUIT_BREAKER_FALLBACKS.labels(
            service="neo4j", layer="l3", fallback_type="pgvector"
        ).inc()

        import asyncpg  # type: ignore[import-untyped]

        pg_dsn = _get_postgres_dsn()
        conn = await asyncpg.connect(dsn=pg_dsn)
        try:
            # Use pgvector for entity similarity
            rows = await conn.fetch(
                """
                SELECT id, content, content_embedding <=> (
                    SELECT content_embedding FROM entities
                    WHERE tenant_id = $1 ORDER BY id LIMIT 1
                ) AS distance
                FROM entities
                WHERE tenant_id = $1
                ORDER BY content_embedding <=> (
                    SELECT content_embedding FROM entities
                    WHERE tenant_id = $1 ORDER BY id LIMIT 1
                )
                LIMIT 20
                """,
                tenant_id,
            )
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    try:
        return await _neo4j_breaker.call(_execute)
    except CircuitBreakerOpen:
        if _neo4j_breaker.config.fallback_enabled:
            return await _pgvector_fallback(cypher, tenant_id, **params)
        raise


async def call_layer3_search(query: str, tenant_id: str) -> dict[str, Any]:
    """Call Layer 3 search endpoint with circuit breaker.

    This is a cross-layer call from L2/L4 to L3 Knowledge service.
    """
    async def _execute() -> dict[str, Any]:
        import aiohttp

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.post(
                "http://l3-knowledge:8080/search",
                json={"query": query, "tenant_id": tenant_id},
                headers={"X-Fabric4L-Source": "circuit_breaker"},
            ) as resp:
                body = await resp.json()
                if resp.status >= 500:
                    raise ServiceUnavailable(f"L3 returned {resp.status}: {body}")
                return {"status": resp.status, "data": body, "source": "l3"}

    async def _cached_fallback(query: str, tenant_id: str) -> dict[str, Any]:
        """Fallback: return cached/stale results from PostgreSQL."""
        logger.info("fallback.l3_cached", tenant_id=tenant_id, query=query[:50])
        CIRCUIT_BREAKER_FALLBACKS.labels(
            service="l3_knowledge", layer="l3", fallback_type="cached"
        ).inc()

        import asyncpg

        pg_dsn = _get_postgres_dsn()
        conn = await asyncpg.connect(dsn=pg_dsn)
        try:
            rows = await conn.fetch(
                "SELECT * FROM search_cache WHERE tenant_id = $1 AND query_hash = md5($2)",
                tenant_id,
                query,
            )
            if rows:
                return {"status": 200, "data": [dict(row) for row in rows], "source": "cache", "stale": True}
            return {"status": 503, "data": [], "source": "fallback", "error": "No cached results available"}
        finally:
            await conn.close()

    try:
        return await _l4_agent_breaker.call(_execute)
    except CircuitBreakerOpen:
        if _l4_agent_breaker.config.fallback_enabled:
            return await _cached_fallback(query, tenant_id)
        raise


async def call_redis_get(key: str) -> bytes | None:
    """Get value from Redis with circuit breaker.

    Fallback: return None (cache miss — will query DB).
    """
    async def _execute() -> bytes | None:
        import redis.asyncio as aioredis  # type: ignore[import-untyped]

        r = aioredis.from_url(_get_redis_uri())
        try:
            value = await r.get(key)
            return value
        finally:
            await r.close()

    try:
        return await _redis_breaker.call(_execute)
    except CircuitBreakerOpen:
        # Cache miss fallback — just return None, caller queries DB
        CIRCUIT_BREAKER_FALLBACKS.labels(
            service="redis", layer="shared", fallback_type="cache_miss"
        ).inc()
        return None


async def call_postgres_query(sql: str, *args: Any) -> list[dict[str, Any]]:
    """Execute SQL against PostgreSQL with circuit breaker.

    No fallback — database is the source of truth. Fail fast.
    """
    async def _execute() -> list[dict[str, Any]]:
        import asyncpg

        conn = await asyncpg.connect(dsn=_get_postgres_dsn())
        try:
            rows = await conn.fetch(sql, *args)
            return [dict(row) for row in rows]
        finally:
            await conn.close()

    return await _postgres_breaker.call(_execute)


async def call_l2_extraction(document_id: str, tenant_id: str, content: str) -> dict[str, Any]:
    """Call Layer 2 extraction service with circuit breaker.

    Fallback: queue for later processing.
    """
    async def _execute() -> dict[str, Any]:
        import aiohttp

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.post(
                "http://l2-extraction:8080/extract",
                json={"document_id": document_id, "tenant_id": tenant_id, "content": content},
            ) as resp:
                body = await resp.json()
                if resp.status >= 500:
                    raise ServiceUnavailable(f"L2 returned {resp.status}")
                return {"status": resp.status, "data": body}

    async def _queue_fallback(document_id: str, tenant_id: str, content: str) -> dict[str, Any]:
        """Fallback: queue extraction for later processing."""
        logger.info("fallback.l2_queued", document_id=document_id, tenant_id=tenant_id)
        CIRCUIT_BREAKER_FALLBACKS.labels(
            service="l2_extraction", layer="l2", fallback_type="queued"
        ).inc()

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://l2-extraction:8080/queue",
                json={"document_id": document_id, "tenant_id": tenant_id, "content": content},
            ) as resp:
                return {"status": 202, "data": {"queued": True}, "source": "fallback"}

    try:
        return await _l2_extraction_breaker.call(_execute)
    except CircuitBreakerOpen:
        if _l2_extraction_breaker.config.fallback_enabled:
            return await _queue_fallback(document_id, tenant_id, content)
        raise


# ---------------------------------------------------------------------------
# Health and Metrics Endpoints
# ---------------------------------------------------------------------------

def get_breaker_metrics() -> dict[str, Any]:
    """Return current state of all circuit breakers for /metrics endpoint."""
    return {
        name: {
            "state": snap.state.value,
            "consecutive_failures": snap.consecutive_failures,
            "success_count": snap.success_count,
            "failure_count": snap.failure_count,
            "fallback_count": snap.fallback_count,
            "last_failure_time": snap.last_failure_time,
            "opened_at": snap.opened_at,
            "layer": snap.config.layer,
        }
        for name, snap in ServiceCircuitBreaker.get_all_snapshots().items()
    }


async def health_check_all() -> dict[str, Any]:
    """Health check that includes circuit breaker status.

    Returns structure suitable for a /health response:
        {
            "status": "healthy" | "degraded",
            "circuit_breakers": { ... },
            "any_open": false | true
        }
    """
    snapshots = ServiceCircuitBreaker.get_all_snapshots()
    any_open = any(s.state == CircuitState.OPEN for s in snapshots.values())
    any_half_open = any(s.state == CircuitState.HALF_OPEN for s in snapshots.values())

    status = "healthy"
    if any_open:
        status = "degraded"
    elif any_half_open:
        status = "degraded"

    return {
        "status": status,
        "circuit_breakers": get_breaker_metrics(),
        "any_open": any_open,
        "any_half_open": any_half_open,
    }


# ---------------------------------------------------------------------------
# Configuration helpers (placeholder — override in production)
# ---------------------------------------------------------------------------

def _get_neo4j_uri() -> str:
    import os
    return os.getenv("NEO4J_URI", "bolt://neo4j-core:7687")


def _get_neo4j_auth() -> tuple[str, str]:
    import os
    return (
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "password"),
    )


def _get_postgres_dsn() -> str:
    import os
    return os.getenv(
        "POSTGRES_DSN",
        "postgresql://postgres:password@postgres-primary:5432/fabric4l",
    )


def _get_redis_uri() -> str:
    import os
    return os.getenv("REDIS_URI", "redis://redis-master:6379/0")


# ---------------------------------------------------------------------------
# FastAPI / Starlette integration helper
# ---------------------------------------------------------------------------

async def circuit_breaker_middleware(request: Any, call_next: Any) -> Any:
    """ASGI middleware that injects circuit breaker headers into responses.

    Usage:
        from starlette.middleware.base import BaseHTTPMiddleware
        app.add_middleware(BaseHTTPMiddleware, dispatch=circuit_breaker_middleware)
    """
    response = await call_next(request)

    # Add breaker status headers
    snapshots = ServiceCircuitBreaker.get_all_snapshots()
    for name, snap in snapshots.items():
        if snap.state != CircuitState.CLOSED:
            response.headers[f"X-Circuit-Breaker-{name}"] = snap.state.value

    return response


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

async def shutdown_breakers() -> None:
    """Reset all breakers during graceful shutdown.

    Call this from your application's lifespan/shutdown handler.
    """
    ServiceCircuitBreaker.reset_all()
    logger.info("circuit_breaker.shutdown_complete")
