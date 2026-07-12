"""Chaos experiments for Fabric 4L 6-layer architecture.

This module implements chaos engineering experiments following the principles
of Netflix Chaos Monkey and Chaos Mesh. Each experiment:

1. Defines a steady-state hypothesis
2. Injects a fault (network, pod, IO, latency)
3. Measures deviation from steady-state
4. Rolls back and reports

Usage:
    pytest tests/chaos/test_service_failure.py -v -m chaos
    make chaos-test  # Run via Makefile target

References:
    - Chaos Engineering Book (O'Reilly)
    - https://chaos-mesh.org/
    - Fabric_4L Architecture v1.2.0
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable

import aiohttp
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHAOS_NAMESPACE = os.getenv("CHAOS_NAMESPACE", "fabric4l")
L1_INGESTION_URL = os.getenv("L1_INGESTION_URL", "http://l1-ingestion:8080")
L2_EXTRACTION_URL = os.getenv("L2_EXTRACTION_URL", "http://l2-extraction:8080")
L3_KNOWLEDGE_URL = os.getenv("L3_KNOWLEDGE_URL", "http://l3-knowledge:8080")
L4_AGENT_URL = os.getenv("L4_AGENT_URL", "http://l4-agent:8080")
L5_GROUND_TRUTH_URL = os.getenv("L5_GROUND_TRUTH_URL", "http://l5-ground-truth:8080")
L6_BENCHMARK_URL = os.getenv("L6_BENCHMARK_URL", "http://l6-benchmark:8080")

POSTGRES_PRIMARY = os.getenv("POSTGRES_PRIMARY", "postgres-primary:5432")
POSTGRES_REPLICA = os.getenv("POSTGRES_REPLICA", "postgres-replica:5432")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-core:7687")
REDIS_URI = os.getenv("REDIS_URI", "redis://redis-master:6379")

# Steady-state thresholds
STEADY_STATE_TIMEOUT_SEC = 5.0
MAX_ACCEPTABLE_P99_MS = 500
MIN_AVAILABILITY_PCT = 99.0


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class FaultType(str, Enum):
    NETWORK_PARTITION = "network_partition"
    POD_KILL = "pod_kill"
    IO_LATENCY = "io_latency"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"


@dataclass
class SteadyStateHypothesis:
    """Defines expected steady-state behavior for a service."""

    name: str
    service_url: str
    health_endpoint: str = "/health"
    max_p99_latency_ms: float = MAX_ACCEPTABLE_P99_MS
    min_availability_pct: float = MIN_AVAILABILITY_PCT
    custom_checks: dict[str, Callable] = field(default_factory=dict)


@dataclass
class ChaosResult:
    """Result of a single chaos experiment."""

    experiment: str
    fault_type: FaultType
    steady_state_met: bool
    deviation_detected: bool
    p99_latency_ms: float
    availability_pct: float
    errors: list[str] = field(default_factory=list)
    recovery_time_sec: float = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class HttpClient:
    """Async HTTP client with timeout and retry semantics."""

    def __init__(self, base_url: str, timeout: float = STEADY_STATE_TIMEOUT_SEC) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> HttpClient:
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._session:
            await self._session.close()

    async def get(self, path: str) -> tuple[int, dict[str, Any]]:
        if not self._session:
            raise RuntimeError("Client not entered")
        url = f"{self.base_url}{path}"
        try:
            async with self._session.get(url) as resp:
                body = await resp.json() if resp.content_type == "application/json" else {}
                return resp.status, body
        except aiohttp.ClientError as e:
            return 0, {"error": str(e)}

    async def post(self, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not self._session:
            raise RuntimeError("Client not entered")
        url = f"{self.base_url}{path}"
        try:
            async with self._session.post(url, json=payload) as resp:
                body = await resp.json() if resp.content_type == "application/json" else {}
                return resp.status, body
        except aiohttp.ClientError as e:
            return 0, {"error": str(e)}


async def check_health(client: HttpClient, endpoint: str = "/health") -> bool:
    """Return True if service health check passes."""
    status, body = await client.get(endpoint)
    return status == 200 and body.get("status") == "healthy"


async def measure_latency(
    client: HttpClient,
    endpoint: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    samples: int = 20,
) -> dict[str, float]:
    """Measure latency percentiles for an endpoint."""
    latencies: list[float] = []
    for _ in range(samples):
        t0 = time.perf_counter()
        if method.upper() == "POST" and payload:
            await client.post(endpoint, payload)
        else:
            await client.get(endpoint)
        latencies.append((time.perf_counter() - t0) * 1000)
        await asyncio.sleep(0.05)

    latencies.sort()
    n = len(latencies)
    return {
        "p50": latencies[n // 2],
        "p95": latencies[int(n * 0.95)],
        "p99": latencies[int(n * 0.99)],
        "max": latencies[-1],
        "min": latencies[0],
    }


@asynccontextmanager
async def steady_state_monitor(
    hypothesis: SteadyStateHypothesis, duration_sec: float = 30.0, interval_sec: float = 1.0
) -> AsyncIterator[list[ChaosResult]]:
    """Monitor steady-state metrics during a chaos experiment."""
    results: list[ChaosResult] = []
    start = time.monotonic()
    async with HttpClient(hypothesis.service_url) as client:
        while time.monotonic() - start < duration_sec:
            healthy = await check_health(client, hypothesis.health_endpoint)
            latencies = await measure_latency(client, hypothesis.health_endpoint)
            results.append(
                ChaosResult(
                    experiment=hypothesis.name,
                    fault_type=FaultType.NETWORK_PARTITION,  # placeholder
                    steady_state_met=healthy and latencies["p99"] <= hypothesis.max_p99_latency_ms,
                    deviation_detected=not healthy,
                    p99_latency_ms=latencies["p99"],
                    availability_pct=100.0 if healthy else 0.0,
                )
            )
            await asyncio.sleep(interval_sec)
    yield results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def chaos_clients() -> dict[str, HttpClient]:
    """Provide HTTP clients for all 6 layers."""
    clients: dict[str, HttpClient] = {}
    for name, url in [
        ("l1", L1_INGESTION_URL),
        ("l2", L2_EXTRACTION_URL),
        ("l3", L3_KNOWLEDGE_URL),
        ("l4", L4_AGENT_URL),
        ("l5", L5_GROUND_TRUTH_URL),
        ("l6", L6_BENCHMARK_URL),
    ]:
        clients[name] = HttpClient(url)
        await clients[name].__aenter__()
    yield clients
    for c in clients.values():
        await c.__aexit__(None, None, None)


@pytest.fixture
def tenant_id() -> str:
    return f"chaos-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Layer 4 Agent Failure Experiments
# ---------------------------------------------------------------------------

@pytest.mark.chaos
class TestLayer4AgentFailure:
    """Simulate Layer 4 failure and verify graceful degradation.

    Layer 4 (Agents/LangGraph) is the orchestration layer. When it fails:
    - L3 should serve cached knowledge graph responses
    - L2 should queue work without dropping extraction tasks
    - L1 should continue ingestion with backpressure
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_layer4_down_layer3_returns_cached(self, chaos_clients: dict[str, HttpClient], tenant_id: str) -> None:
        """When L4 is unreachable, L3 should serve cached responses.

        Steady-state hypothesis:
            - L4 health check returns 200
            - L3 /search endpoint p99 < 500ms
            - L3 cache hit rate > 80%

        Fault injection:
            - Network partition between L3 and L4 (via Chaos Mesh)

        Expected behavior:
            - L3 detects L4 unavailability via circuit breaker
            - L3 serves cached knowledge graph results
            - HTTP 200 responses with stale-while-revalidate header
            - No request drops
        """
        l3 = chaos_clients["l3"]
        l4 = chaos_clients["l4"]

        # 1. Verify steady-state
        assert await check_health(l4), "L4 should be healthy before experiment"
        baseline = await measure_latency(l3, "/search", method="POST", payload={"query": "test", "tenant_id": tenant_id})
        assert baseline["p99"] < MAX_ACCEPTABLE_P99_MS, f"L3 baseline p99 {baseline['p99']}ms too high"

        # 2. Inject fault: simulate L4 network partition
        #    (In CI this applies the Chaos Mesh NetworkPartition CRD)
        await self._inject_l4_partition(True)

        try:
            # 3. Verify graceful degradation
            for attempt in range(10):
                status, body = await l3.post("/search", {"query": "chaos test", "tenant_id": tenant_id})
                assert status == 200, f"L3 returned {status} when L4 is partitioned"
                assert body.get("source") in ("cache", "fallback"), "L3 should serve from cache/fallback"
                assert "X-Cache-Status" in body.get("headers", {}), "L3 should indicate cache status"
                await asyncio.sleep(1)

            # 4. Measure degraded latency (should be < 2x baseline)
            degraded = await measure_latency(l3, "/search", method="POST", payload={"query": "test", "tenant_id": tenant_id}, samples=10)
            assert degraded["p99"] < baseline["p99"] * 2, f"L3 degraded p99 {degraded['p99']}ms exceeds 2x baseline"

        finally:
            # 5. Rollback
            await self._inject_l4_partition(False)
            await asyncio.sleep(5)
            assert await check_health(l4), "L4 should recover after partition removal"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_layer4_slow_layer2_queues_work(self, chaos_clients: dict[str, HttpClient], tenant_id: str) -> None:
        """When L4 is slow, L2 should queue work without dropping.

        Steady-state hypothesis:
            - L4 processes extraction tasks with p99 < 500ms
            - L2 queue depth < 100
            - Zero task drops

        Fault injection:
            - IO latency on L4 pods (100ms injected)

        Expected behavior:
            - L2 detects L4 slowness via circuit breaker HALF_OPEN state
            - L2 queues extraction tasks in Redis-backed queue
            - Queue depth grows but stabilizes
            - Zero message drops
            - Tasks processed after L4 recovers
        """
        l2 = chaos_clients["l2"]
        l4 = chaos_clients["l4"]

        # 1. Verify steady-state
        assert await check_health(l4)
        status, baseline_queue = await l2.get("/metrics/queue_depth")
        assert status == 200
        baseline_depth = baseline_queue.get("depth", 0)
        assert baseline_depth < 100, f"L2 queue depth {baseline_depth} too high at baseline"

        # 2. Inject fault: IO latency on L4
        await self._inject_l4_io_latency(latency_ms=100)

        try:
            # 3. Flood L2 with extraction tasks
            tasks_sent = 50
            for i in range(tasks_sent):
                status, _ = await l2.post(
                    "/extract",
                    {"document_id": f"doc-{i}", "tenant_id": tenant_id, "content": "chaos test content"},
                )
                assert status == 202, f"L2 rejected task with {status}"
                await asyncio.sleep(0.05)

            # 4. Verify queue absorbs tasks
            await asyncio.sleep(2)
            status, queue_metrics = await l2.get("/metrics/queue_depth")
            assert status == 200
            queue_depth = queue_metrics.get("depth", 0)
            assert queue_depth > 0, "L2 queue should have buffered tasks"
            assert queue_metrics.get("dropped", 0) == 0, "L2 should not drop tasks"

            # 5. Verify tasks eventually processed (after IO latency removed)
            await self._inject_l4_io_latency(latency_ms=0)
            await asyncio.sleep(10)
            status, processed = await l2.get("/metrics/processed")
            assert status == 200
            assert processed.get("count", 0) >= tasks_sent, "L2 should process all queued tasks"

        finally:
            await self._inject_l4_io_latency(latency_ms=0)
            await asyncio.sleep(3)

    @pytest.mark.asyncio
    async def test_layer4_circuit_breaker_opens_on_repeated_failure(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Verify circuit breaker transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.

        Steps:
            1. Verify breaker is CLOSED
            2. Kill L4 pod repeatedly (5 times)
            3. Verify breaker transitions to OPEN
            4. Wait recovery_timeout (30s)
            5. Verify breaker is HALF_OPEN
            6. Restore L4
            7. Verify breaker returns to CLOSED
        """
        l3 = chaos_clients["l3"]

        # 1. Breaker should start CLOSED
        status, breaker_state = await l3.get("/debug/circuit_breakers/l4_agent")
        assert status == 200
        assert breaker_state.get("state") == "closed", f"Breaker state: {breaker_state}"

        # 2. Kill L4 pod 5 times
        for _ in range(5):
            await self._kill_l4_pod()
            await asyncio.sleep(2)

        # 3. Breaker should be OPEN
        await asyncio.sleep(1)
        status, breaker_state = await l3.get("/debug/circuit_breakers/l4_agent")
        assert status == 200
        assert breaker_state.get("state") == "open", f"Breaker should be OPEN after failures, got: {breaker_state}"

        # 4. Wait recovery timeout
        await asyncio.sleep(30)

        # 5. Breaker should be HALF_OPEN
        status, breaker_state = await l3.get("/debug/circuit_breakers/l4_agent")
        assert breaker_state.get("state") == "half_open", f"Breaker should be HALF_OPEN, got: {breaker_state}"

        # 6. Restore L4 (scale back up)
        await self._restore_l4_pod()
        await asyncio.sleep(5)

        # 7. Breaker should be CLOSED again
        status, breaker_state = await l3.get("/debug/circuit_breakers/l4_agent")
        assert breaker_state.get("state") == "closed", f"Breaker should be CLOSED after recovery, got: {breaker_state}"

    # --- Fault injection helpers ---

    async def _inject_l4_partition(self, enabled: bool) -> None:
        """Apply or remove Chaos Mesh NetworkPartition for L4."""
        action = "apply" if enabled else "delete"
        rc = os.system(f"kubectl {action} -f k8s/chaos-mesh/network-partition.yaml -n {CHAOS_NAMESPACE}")
        assert rc == 0, f"Failed to {action} network partition"
        await asyncio.sleep(2)

    async def _inject_l4_io_latency(self, latency_ms: int) -> None:
        """Apply or remove IOChaos on L4 pods."""
        if latency_ms > 0:
            # Patch the latency value dynamically
            rc = os.system(
                f"sed 's/{{LATENCY_MS}}/{latency_ms}/' k8s/chaos-mesh/io-latency.yaml | "
                f"kubectl apply -n {CHAOS_NAMESPACE} -f -"
            )
        else:
            rc = os.system(f"kubectl delete -f k8s/chaos-mesh/io-latency.yaml -n {CHAOS_NAMESPACE} --ignore-not-found")
        assert rc == 0, f"Failed to inject IO latency {latency_ms}ms"
        await asyncio.sleep(2)

    async def _kill_l4_pod(self) -> None:
        """Kill a random L4 pod to simulate crash."""
        rc = os.system(
            f"kubectl delete pod -l app=l4-agent -n {CHAOS_NAMESPACE} --force --grace-period=0"
        )
        assert rc == 0, "Failed to kill L4 pod"

    async def _restore_l4_pod(self) -> None:
        """Ensure L4 deployment is at desired replica count."""
        rc = os.system(
            f"kubectl rollout status deployment/l4-agent -n {CHAOS_NAMESPACE} --timeout=120s"
        )
        assert rc == 0, "L4 pod failed to restore"


# ---------------------------------------------------------------------------
# Database Failure Experiments
# ---------------------------------------------------------------------------

@pytest.mark.chaos
class TestDatabaseFailure:
    """Simulate database failures and verify failover behavior.

    PostgreSQL:
        - Primary failure should trigger automatic failover to read replica
        - L1/L2 should continue writing via replica promotion

    Neo4j:
        - Cluster partition should trigger pgvector fallback in L3
        - Knowledge graph queries degrade to vector similarity search
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.skipif(
        os.getenv("SKIP_DB_FAILOVER") == "1",
        reason="DB failover test requires dedicated DB cluster"
    )
    async def test_postgres_failover_to_replica(self, chaos_clients: dict[str, HttpClient], tenant_id: str) -> None:
        """Verify automatic failover to read replica.

        Steady-state hypothesis:
            - PostgreSQL primary accepts writes
            - Replication lag < 1s
            - L1 ingestion endpoint p99 < 500ms

        Fault injection:
            - Kill PostgreSQL primary pod
            - Patroni should promote replica

        Expected behavior:
            - Automatic failover within 30s
            - Zero data loss (sync replication)
            - L1 continues ingesting after brief pause
        """
        l1 = chaos_clients["l1"]

        # 1. Baseline write
        doc = {"tenant_id": tenant_id, "content": "pre-failover doc", "source": "chaos"}
        status, _ = await l1.post("/ingest", doc)
        assert status == 201, "Baseline write failed"

        # 2. Kill primary
        await self._kill_postgres_primary()

        try:
            # 3. Verify failover detection (may fail briefly)
            max_wait = 60
            for elapsed in range(0, max_wait, 5):
                status, health = await l1.get("/health")
                if status == 200 and health.get("postgres_status") == "active":
                    break
                await asyncio.sleep(5)
            else:
                pytest.fail("PostgreSQL failover did not complete within 60s")

            # 4. Verify writes work on promoted replica
            doc = {"tenant_id": tenant_id, "content": "post-failover doc", "source": "chaos"}
            status, body = await l1.post("/ingest", doc)
            assert status == 201, f"Write after failover failed: {body}"

            # 5. Verify replication re-established
            await asyncio.sleep(5)
            status, repl = await l1.get("/metrics/replication")
            assert status == 200
            assert repl.get("lag_seconds", 999) < 5, f"Replication lag too high: {repl}"

        finally:
            await self._restore_postgres_primary()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_neo4j_partition_layer3_switches_to_pgvector(self, chaos_clients: dict[str, HttpClient], tenant_id: str) -> None:
        """When Neo4j is partitioned, L3 falls back to pgvector.

        Steady-state hypothesis:
            - Neo4j cluster responds to Cypher queries
            - L3 /graph/query p99 < 500ms

        Fault injection:
            - Network partition isolating Neo4j core servers

        Expected behavior:
            - L3 circuit breaker for Neo4j transitions to OPEN
            - L3 falls back to pgvector for similarity search
            - Responses include header X-Fallback: pgvector
            - HTTP 200 (not 500)
        """
        l3 = chaos_clients["l3"]

        # 1. Baseline graph query
        baseline = await measure_latency(
            l3, "/graph/query", method="POST",
            payload={"cypher": "MATCH (n) RETURN count(n)", "tenant_id": tenant_id}
        )
        assert baseline["p99"] < MAX_ACCEPTABLE_P99_MS

        # 2. Partition Neo4j
        await self._partition_neo4j(True)

        try:
            # 3. Query should still succeed via fallback
            for attempt in range(10):
                status, body = await l3.post(
                    "/graph/query",
                    {"cypher": "MATCH (n {tenant_id: $tid}) RETURN n", "tenant_id": tenant_id},
                )
                assert status == 200, f"L3 returned {status} during Neo4j partition"
                headers = body.get("headers", {})
                assert headers.get("X-Fallback") == "pgvector", f"Expected pgvector fallback, got: {headers}"
                await asyncio.sleep(1)

            # 4. Verify circuit breaker state
            status, breaker = await l3.get("/debug/circuit_breakers/neo4j")
            assert breaker.get("state") in ("open", "half_open"), f"Neo4j breaker should be open: {breaker}"

        finally:
            await self._partition_neo4j(False)

    @pytest.mark.asyncio
    async def test_postgres_connection_pool_exhaustion_recovery(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Verify services recover after connection pool exhaustion.

        Steps:
            1. Baseline: measure connection pool usage
            2. Flood with concurrent requests exceeding pool size
            3. Verify queueing (not crashing)
            4. Back off and verify pool recovers
        """
        l1 = chaos_clients["l1"]

        async def flood() -> list[int]:
            statuses: list[int] = []
            for _ in range(100):
                st, _ = await l1.post("/ingest", {"tenant_id": "pool-test", "content": "x"})
                statuses.append(st)
                await asyncio.sleep(0.01)
            return statuses

        statuses = await flood()
        # Some 503s are acceptable under extreme load; no 500s allowed
        assert all(s in (201, 202, 429, 503) for s in statuses), f"Unexpected errors: {set(statuses) - {201, 202, 429, 503}}"

        # Recovery
        await asyncio.sleep(5)
        status, _ = await l1.get("/health")
        assert status == 200, "Service did not recover after pool exhaustion"

    # --- Fault injection helpers ---

    async def _kill_postgres_primary(self) -> None:
        rc = os.system(
            f"kubectl delete pod -l app=postgres-primary,role=primary -n {CHAOS_NAMESPACE} --force --grace-period=0"
        )
        assert rc == 0
        await asyncio.sleep(2)

    async def _restore_postgres_primary(self) -> None:
        # Patroni auto-restores; just wait
        rc = os.system(
            f"kubectl rollout status statefulset/postgres -n {CHAOS_NAMESPACE} --timeout=120s"
        )
        assert rc == 0

    async def _partition_neo4j(self, enabled: bool) -> None:
        action = "apply" if enabled else "delete"
        rc = os.system(
            f"kubectl {action} -f k8s/chaos-mesh/network-partition-neo4j.yaml -n {CHAOS_NAMESPACE}"
        )
        assert rc == 0
        await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# Redis Failure Experiments
# ---------------------------------------------------------------------------

@pytest.mark.chaos
class TestRedisFailure:
    """Simulate Redis cache failures.

    All layers use Redis for caching and pub/sub. When Redis fails:
    - Services must continue operating (cache-aside pattern)
    - Latency increases but availability is preserved
    - Circuit breaker prevents cascading failures
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_redis_down_services_degrade_gracefully(self, chaos_clients: dict[str, HttpClient], tenant_id: str) -> None:
        """Services should work without cache (slower but functional).

        Steady-state hypothesis:
            - Redis responds in < 5ms
            - Cache hit rate > 70%
            - L3 query p99 < 500ms

        Fault injection:
            - Kill Redis master pod

        Expected behavior:
            - L3 queries still return 200 (direct DB query)
            - Latency increases 2-5x (acceptable)
            - No 500 errors
            - Circuit breaker for Redis opens
            - Auto-recovery when Redis restored
        """
        l3 = chaos_clients["l3"]

        # 1. Baseline with cache warm
        for _ in range(20):
            await l3.post("/search", {"query": "warm cache", "tenant_id": tenant_id})
        baseline = await measure_latency(l3, "/search", method="POST", payload={"query": "warm cache", "tenant_id": tenant_id})
        assert baseline["p99"] < MAX_ACCEPTABLE_P99_MS

        # 2. Kill Redis
        await self._kill_redis_master()

        try:
            # 3. Verify service still works (slower)
            degraded = await measure_latency(
                l3, "/search", method="POST",
                payload={"query": "warm cache", "tenant_id": tenant_id},
                samples=10,
            )
            assert degraded["p99"] < baseline["p99"] * 5, (
                f"Degraded latency {degraded['p99']}ms exceeds 5x baseline {baseline['p99']}ms"
            )

            # 4. Verify no errors
            for _ in range(10):
                status, body = await l3.post("/search", {"query": "test", "tenant_id": tenant_id})
                assert status == 200, f"L3 returned {status} when Redis is down: {body}"
                await asyncio.sleep(0.5)

            # 5. Verify circuit breaker opened
            status, breaker = await l3.get("/debug/circuit_breakers/redis")
            assert breaker.get("state") in ("open", "half_open"), f"Redis breaker should be open: {breaker}"

        finally:
            # 6. Restore Redis
            await self._restore_redis()
            await asyncio.sleep(5)

            # 7. Verify cache warms back up
            warmed = await measure_latency(
                l3, "/search", method="POST",
                payload={"query": "warm cache", "tenant_id": tenant_id},
                samples=10,
            )
            assert warmed["p99"] < MAX_ACCEPTABLE_P99_MS, f"Latency did not recover: {warmed['p99']}ms"

    @pytest.mark.asyncio
    async def test_redis_slow_rejected_by_circuit_breaker(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Slow Redis should be short-circuited to prevent cascading latency.

        Fault injection:
            - IO latency on Redis (200ms read/write delay)

        Expected behavior:
            - Circuit breaker transitions to OPEN within 15s
            - Services bypass Redis entirely
            - No request latency > 2s
        """
        l3 = chaos_clients["l3"]

        # Inject latency
        await self._inject_redis_latency(200)

        try:
            await asyncio.sleep(15)
            status, breaker = await l3.get("/debug/circuit_breakers/redis")
            assert breaker.get("state") == "open", f"Breaker should be OPEN for slow Redis: {breaker}"

            # Requests should bypass Redis
            t0 = time.perf_counter()
            status, _ = await l3.post("/search", {"query": "test", "tenant_id": "slow-redis"})
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert status == 200
            assert elapsed_ms < 2000, f"Request too slow even with breaker: {elapsed_ms}ms"

        finally:
            await self._inject_redis_latency(0)

    @pytest.mark.asyncio
    async def test_redis_pubsub_failover(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Verify pub/sub messages are not lost during Redis failover.

        Steps:
            1. Subscribe L2 to ingestion events
            2. Send 100 ingestion events
            3. Kill Redis during processing
            4. Verify all events eventually processed
        """
        l1 = chaos_clients["l1"]
        l2 = chaos_clients["l2"]

        # Pre-send events
        event_ids = [f"evt-{i}" for i in range(50)]
        for eid in event_ids:
            await l1.post("/ingest", {"document_id": eid, "tenant_id": "pubsub-test", "content": "x"})

        # Kill Redis mid-processing
        await self._kill_redis_master()
        await asyncio.sleep(2)
        await self._restore_redis()
        await asyncio.sleep(5)

        # Verify all events processed
        status, metrics = await l2.get("/metrics/processed")
        assert status == 200
        # At minimum, no events should be permanently lost
        assert metrics.get("lost", 0) == 0, f"Events lost during Redis failover: {metrics}"

    # --- Fault injection helpers ---

    async def _kill_redis_master(self) -> None:
        rc = os.system(
            f"kubectl delete pod -l app=redis,role=master -n {CHAOS_NAMESPACE} --force --grace-period=0"
        )
        assert rc == 0
        await asyncio.sleep(2)

    async def _restore_redis(self) -> None:
        rc = os.system(
            f"kubectl rollout status statefulset/redis -n {CHAOS_NAMESPACE} --timeout=120s"
        )
        assert rc == 0

    async def _inject_redis_latency(self, latency_ms: int) -> None:
        if latency_ms > 0:
            rc = os.system(
                f"sed 's/{{LATENCY_MS}}/{latency_ms}/' k8s/chaos-mesh/io-latency-redis.yaml | "
                f"kubectl apply -n {CHAOS_NAMESPACE} -f -"
            )
        else:
            rc = os.system(
                f"kubectl delete -f k8s/chaos-mesh/io-latency-redis.yaml -n {CHAOS_NAMESPACE} --ignore-not-found"
            )
        assert rc == 0
        await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# Cross-Layer Cascading Failure Experiments
# ---------------------------------------------------------------------------

@pytest.mark.chaos
class TestCascadingFailure:
    """Verify the entire stack resists cascading failures.

    These are the most critical experiments: they verify that a failure
    in one layer does not bring down the entire system.
    """

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_layer_cascade_all_layers_survive(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Kill one pod in each layer sequentially; all health checks should pass.

        This is the "chaos monkey" baseline: random pod kills should not
        cause system-wide outages.
        """
        layers = ["l1", "l2", "l3", "l4", "l5", "l6"]
        for layer in layers:
            await self._kill_random_pod(layer)
            await asyncio.sleep(3)
            # All layers should still report healthy (via K8s readiness probes)
            for check_layer in layers:
                client = chaos_clients[check_layer]
                status, _ = await client.get("/health")
                assert status == 200, f"{check_layer} unhealthy after killing {layer} pod"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_circuit_breaker_prevents_cascade(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Verify circuit breakers isolate failures before they cascade.

        Steps:
            1. Verify all breakers are CLOSED
            2. Kill L4, L3 dependency
            3. Verify L1/L2 unaffected (their breakers for downstream stay OPEN)
            4. Verify L3 serves fallback
        """
        l1 = chaos_clients["l1"]
        l2 = chaos_clients["l2"]
        l3 = chaos_clients["l3"]

        # Kill L4 and L3's Neo4j
        await self._kill_random_pod("l4")
        await self._partition_neo4j_for_l3()

        await asyncio.sleep(5)

        # L1 and L2 should still be fully operational
        status, _ = await l1.get("/health")
        assert status == 200, "L1 should be unaffected by L4 failure"
        status, _ = await l2.get("/health")
        assert status == 200, "L2 should be unaffected by L4 failure"

        # L3 should serve fallback
        status, body = await l3.post("/search", {"query": "cascade test", "tenant_id": "cascade"})
        assert status == 200, f"L3 should serve fallback during cascade: {body}"

    async def _kill_random_pod(self, layer: str) -> None:
        rc = os.system(
            f"kubectl delete pod -l app={layer}-ingestion -n {CHAOS_NAMESPACE} --force --grace-period=0 2>/dev/null || "
            f"kubectl delete pod -l app={layer}-extraction -n {CHAOS_NAMESPACE} --force --grace-period=0 2>/dev/null || "
            f"kubectl delete pod -l app={layer}-knowledge -n {CHAOS_NAMESPACE} --force --grace-period=0 2>/dev/null || "
            f"kubectl delete pod -l app={layer}-agent -n {CHAOS_NAMESPACE} --force --grace-period=0 2>/dev/null || "
            f"kubectl delete pod -l app={layer}-ground-truth -n {CHAOS_NAMESPACE} --force --grace-period=0 2>/dev/null || "
            f"kubectl delete pod -l app={layer}-benchmark -n {CHAOS_NAMESPACE} --force --grace-period=0 2>/dev/null || "
            f"kubectl delete pod -l app={layer} -n {CHAOS_NAMESPACE} --force --grace-period=0"
        )
        assert rc == 0
        await asyncio.sleep(3)

    async def _partition_neo4j_for_l3(self) -> None:
        rc = os.system(
            f"kubectl apply -f k8s/chaos-mesh/network-partition-neo4j.yaml -n {CHAOS_NAMESPACE}"
        )
        assert rc == 0


# ---------------------------------------------------------------------------
# Metrics & Reporting
# ---------------------------------------------------------------------------

@pytest.mark.chaos
class TestChaosMetrics:
    """Verify chaos experiments emit proper metrics."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_emitted(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Verify Prometheus metrics for circuit breakers are present."""
        l3 = chaos_clients["l3"]
        status, metrics = await l3.get("/metrics")
        assert status == 200
        metrics_text = metrics.get("raw", "")
        assert "circuit_breaker_state" in metrics_text, "Missing circuit_breaker_state metric"
        assert "circuit_breaker_failures_total" in metrics_text, "Missing circuit_breaker_failures_total metric"
        assert "circuit_breaker_successes_total" in metrics_text, "Missing circuit_breaker_successes_total metric"

    @pytest.mark.asyncio
    async def test_chaos_experiment_traces(self, chaos_clients: dict[str, HttpClient]) -> None:
        """Verify OpenTelemetry traces include chaos experiment tags."""
        l3 = chaos_clients["l3"]
        status, trace_info = await l3.get("/debug/trace/chaos-test")
        assert status == 200
        assert trace_info.get("chaos.experiment") is not None, "Missing chaos experiment trace tag"
        assert trace_info.get("chaos.fault_type") is not None, "Missing chaos fault type trace tag"
