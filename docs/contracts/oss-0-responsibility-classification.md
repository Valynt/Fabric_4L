# OSS-0 Responsibility Classification and Migration Boundaries

**Author:** Manus AI  
**Scope:** Fabric_4L cache, resilience, and task-scheduler infrastructure  
**Sprint:** OSS-0: Responsibility Classification and Port Scaffolding

## Purpose

OSS-0 establishes the safety boundary for future open-source substitution. The sprint intentionally avoids changing runtime defaults. Its goal is to classify current responsibilities, freeze observable behavior with characterization tests, and introduce stable ports that allow the current legacy implementations and future OSS-backed implementations to be exercised behind the same application contract.

> The operating principle for OSS-0 is to **retire infrastructure risk, not product semantics**. Generic storage, retry, queueing, and circuit-breaker mechanics may move behind OSS-backed adapters later. Tenant isolation, governance decisions, workflow semantics, observable result shapes, and Fabric-specific audit behavior remain first-class Fabric responsibilities.

## Classification Matrix

| Surface | Current Implementation | Generic Infrastructure Responsibilities | Fabric-Specific Responsibilities | OSS-0 Boundary Decision |
|---|---|---|---|---|
| L3 cache | `services/layer3-knowledge/src/cache/redis_cache.py` | JSON serialization, Redis get/set/delete, TTL handling, pattern invalidation, existence checks, increment operations, connection lifecycle, stats retrieval, cache stampede locking. | Stable key-generation behavior, fallback-to-`None`/`False` error semantics, request deduplication operation keys, result-cache TTL behavior, global cache manager initialization semantics. | Introduce a `CachePort` and `LegacyCacheAdapter` that wrap the existing `RedisCache` without replacing Redis behavior. Future `aiocache` pilots must satisfy the same port tests. |
| L4 resilience | `services/layer4-agents/src/resilience.py` | Token-bucket math, dependency circuit-breaker state transitions, recovery timeout handling, registry reuse. | Per-tenant fairness, tenant bucket isolation, retry-after reporting, service-name observability, exception metadata used by callers. | Introduce separate `TenantRateLimitPort` and `DependencyCircuitBreakerPort` adapters. Generic breaker logic can later be replaced, but tenant rate limiting remains Fabric governance. |
| L4 scheduler | `services/layer4-agents/src/layer4_agents/engine/scheduler.py` | Priority queueing, scheduled-time ordering, concurrency backpressure, timeout wrapping, retry scheduling, callback execution. | Tenant context propagation, workflow execution payload shape, capability handler dispatch, task history schema, workflow-instance linkage, tenant-filtered listing and cancellation. | Introduce a `TaskExecutionPort` and legacy adapter for the existing scheduler. Future Celery-style execution must preserve Fabric task metadata and result contracts. |

## Cache Boundary

The cache surface combines low-level Redis operations and higher-level request coalescing. OSS-0 treats simple storage operations as substitutable infrastructure but treats the surrounding behavioral contract as application-owned. The most important observable behaviors are error-to-safe-default handling, key prefixing, TTL propagation, cache-stampede prevention through per-key locks, and request deduplication across identical operation/parameter pairs.

| Behavior to Freeze | Reason |
|---|---|
| `get()` returns `None` on misses and Redis errors. | Callers currently rely on safe cache degradation rather than exception propagation. |
| `set()` and `delete()` return boolean success values. | The cache is optional infrastructure and should fail soft. |
| `clear_pattern()` returns the number of deleted keys and returns `0` on failure. | Pattern invalidation is operationally useful but non-fatal. |
| `CacheManager.get_or_set()` executes the factory once for concurrent same-key misses. | This is the cache-stampede protection that an OSS-backed adapter must preserve or explicitly replace. |
| `RequestDeduplicator.execute()` shares in-flight results for identical operation/parameter hashes. | This behavior is product-relevant for expensive GraphRAG and analytics paths. |

## Resilience Boundary

The resilience module contains two different classes of responsibility that should not be collapsed. The circuit breaker is primarily dependency resilience and can be mapped to an OSS-backed implementation later. The tenant rate limiter is Fabric governance because it expresses fairness and abuse protection across tenants.

| Behavior to Freeze | Reason |
|---|---|
| A new tenant starts with an independent full token bucket. | Tenant isolation and fairness are product semantics. |
| Depleted tenants receive a retry-after estimate rather than an implementation-specific error. | API and caller behavior depend on stable backoff guidance. |
| Circuit breakers open after the configured threshold, reject while open, transition to half-open after timeout, and close after successful probe calls. | These are generic resilience semantics suitable for OSS parity testing. |
| `CircuitBreakerOpen` carries both `service` and `retry_after`. | Observability and fallback logic depend on these fields. |
| `CircuitBreakerRegistry` reuses breaker instances by service name. | Service-level isolation must remain stable across adapter implementations. |

## Scheduler Boundary

The scheduler is the highest-risk substitution surface. It is not just a queue. It owns Fabric-specific task metadata, tenant context propagation, workflow execution wrapping, status serialization, and task-history accounting. A future Celery-backed implementation should therefore start as a task execution backend behind a port, not as a wholesale replacement for orchestration semantics.

| Behavior to Freeze | Reason |
|---|---|
| Pending tasks are ordered by priority and scheduled time. | Scheduling behavior is externally visible through execution order and pending lists. |
| Tenant context is preserved across retry scheduling. | Async execution must not lose row-level-security context. |
| `workflow_execution` tasks call `workflow.run(initial_state, thread_id=workflow_id)` and return the current wrapper shape. | The orchestration controller depends on this execution contract. |
| Unknown capabilities fail with a runtime error. | Silent drops would hide configuration errors. |
| Stats and task-history dictionaries preserve their current key names. | Tests, route handlers, and operational diagnostics rely on stable shapes. |

## Port Introduction Rules

Ports introduced during OSS-0 are deliberately thin. They must express the current application contract without leaking library-specific APIs. They must also make the legacy implementation the default adapter so the sprint remains behavior-preserving.

| Port | Required Methods | Legacy Adapter | Future Adapter Candidate |
|---|---|---|---|
| `CachePort` | `get`, `set`, `delete`, `clear_pattern`, `exists`, `increment`, `get_stats` | Existing `RedisCache` via `LegacyCacheAdapter` | `aiocache`-backed adapter |
| `TenantRateLimitPort` | `check_rate_limit`, `get_retry_after`, `get_bucket_state` | Existing `TenantRateLimiter` via `LegacyTenantRateLimitAdapter` | Custom Fabric adapter remains likely |
| `DependencyCircuitBreakerPort` | `call`, `get_state` | Existing `CircuitBreaker` via `LegacyCircuitBreakerAdapter` | Library-backed dependency breaker |
| `TaskExecutionPort` | `submit`, `cancel`, `get_status`, `list_pending`, `list_running`, `get_stats` | Existing `TaskScheduler` via `LegacyTaskExecutionAdapter` | Celery/distributed queue adapter |

## OSS-0 Exit Criteria

OSS-0 is complete when the current behavior is documented and covered by tests, and when current implementations can be reached through stable ports without changing runtime defaults.

| Gate | Acceptance Criteria |
|---|---|
| Classification gate | Cache, resilience, and scheduler responsibilities are categorized as generic infrastructure or Fabric-specific semantics. |
| Characterization gate | Focused tests freeze the current observable behavior that any OSS-backed adapter must preserve. |
| Interface gate | Ports exist for cache, tenant limiting, dependency circuit breaking, and task execution. |
| Legacy-adapter gate | Legacy adapters delegate to the current implementations and are covered by focused tests. |
| Default-behavior gate | Existing initialization paths and runtime defaults remain unchanged. |
| Promotion gate | The sprint recommends a single low-risk OSS-1 pilot only after tests pass. |

## Recommended OSS-1 Candidate

If OSS-0 validates cleanly, the first substitution pilot should be `CachePort` parity with an `aiocache`-backed implementation in shadow or test-only mode. The scheduler should remain in decomposition until task execution, workflow orchestration, tenant context propagation, and durable state responsibilities are fully separated.
