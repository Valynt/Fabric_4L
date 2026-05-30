# OSS-0 Validation Evidence

**Author:** Manus AI  
**Date:** 2026-05-05  
**Scope:** Cache, resilience, and scheduler responsibility classification; characterization tests; and legacy-backed ports for future OSS substitution.

## Summary

OSS-0 established migration scaffolding without changing runtime defaults. The sprint classified the current Layer 3 cache, Layer 4 resilience, and Layer 4 scheduler responsibilities; froze observable behavior with characterization tests; and introduced stable ports with legacy adapters so future OSS-backed implementations can be evaluated behind the same contracts.

The implementation intentionally avoided enabling `aiocache`, `pybreaker`, Celery, or another OSS default in this sprint. The purpose was to make a future replacement safe by preserving **tenant-aware behavior**, **retry semantics**, **deduplication behavior**, and **scheduler result shape** before any implementation swap.

| Area | OSS-0 Outcome | Runtime Default Changed |
|---|---|---:|
| Layer 3 cache | Added `CachePort`, `LegacyCacheAdapter`, and cache characterization tests for stampede protection and request deduplication. | No |
| Layer 4 resilience | Added resilience ports that separate dependency circuit breaking from tenant governance. | No |
| Layer 4 scheduler | Added a task-execution port and legacy adapter around the existing scheduler; added scheduler characterization tests. | No |
| Documentation | Added responsibility classification and validation evidence documents. | No |

## Files Changed

| File | Purpose |
|---|---|
| `docs/contracts/oss-0-responsibility-classification.md` | Records the migration classification for cache, resilience, and scheduler responsibilities. |
| `docs/contracts/oss-0-validation-evidence.md` | Records the OSS-0 validation gates and implementation evidence. |
| `services/layer3-knowledge/src/cache/ports.py` | Defines the Layer 3 cache port and legacy adapter. |
| `services/layer3-knowledge/src/cache/__init__.py` | Exports the new cache port symbols without removing existing exports. |
| `services/layer3-knowledge/tests/test_cache_characterization.py` | Freezes cache manager stampede protection and request-deduplication behavior. |
| `services/layer3-knowledge/tests/test_cache_ports.py` | Verifies the legacy cache adapter delegates through the stable port contract. |
| `services/layer3-knowledge/tests/conftest.py` | Lazily constructs the API app so cache-only tests do not trigger unrelated API imports at collection time. |
| `services/layer4-agents/src/resilience_ports.py` | Defines Layer 4 resilience ports and legacy adapters. |
| `services/layer4-agents/src/layer4_agents/engine/ports.py` | Defines the task-execution port and legacy scheduler adapter. |
| `services/layer4-agents/src/layer4_agents/engine/__init__.py` | Exports task-execution port symbols without changing scheduler defaults. |
| `services/layer4-agents/tests/unit/test_oss0_ports.py` | Verifies Layer 4 port adapters preserve current behavior boundaries. |
| `services/layer4-agents/tests/unit/test_task_scheduler.py` | Adds OSS-0 scheduler characterization coverage for retry tenant preservation and public result shape. |

## Validation Results

The focused OSS-0 validation passed for the new Layer 3 and Layer 4 tests. A broader Layer 4 unit validation also passed after using both package-root and source-root paths, matching the repository's mixed import style in existing tests.

| Gate | Command | Result |
|---|---|---|
| Layer 3 focused cache validation | `PYTHONPATH=.:../../packages/shared/src pytest tests/test_cache_characterization.py tests/test_cache_ports.py -q` from `services/layer3-knowledge` | Passed: `6 passed in 0.53s` |
| Combined OSS-0 focused validation | `PYTHONPATH=services/layer3-knowledge:packages/shared/src pytest services/layer3-knowledge/tests/test_cache_characterization.py services/layer3-knowledge/tests/test_cache_ports.py -q && cd services/layer4-agents && PYTHONPATH=src:../../packages/shared/src pytest tests/unit/test_task_scheduler.py tests/unit/test_oss0_ports.py -q` | Passed: Layer 3 `6 passed`; Layer 4 `32 passed` |
| Layer 4 broad unit validation | `PYTHONPATH=.:src:../../packages/shared/src pytest tests/unit -q` from `services/layer4-agents` | Passed: `191 passed, 13 warnings in 1.50s` |
| Python compile check | `python3.11 -m py_compile` over all new OSS-0 modules and tests | Passed: no compile errors |

## Behavior Frozen by Characterization Tests

The characterization tests intentionally verify current observable behavior rather than prescribe a new architecture. This lets future OSS-backed adapters run against the same expectations before promotion.

| Behavior | Test Coverage Added |
|---|---|
| Cache stampede protection | Concurrent `CacheManager.get_or_set` calls for the same missing key share one factory execution and write one cache value. |
| Cache-hit bypass | Cached values bypass factory execution and preserve the cached value shape. |
| Request deduplication key stability | Deduplication keys use sorted parameter hashes, so parameter order does not change the key. |
| Request deduplication cleanup | Concurrent identical requests share one in-flight result and clean their pending lock afterward. |
| Scheduler retry tenant preservation | Retried tasks preserve tenant context across scheduler behavior. |
| Scheduler public result shape | Scheduler handler results remain wrapped in the existing typed result payload rather than being replaced by raw handler output. |
| Legacy adapter delegation | Cache, resilience, and scheduler adapters delegate to existing implementations through stable contracts. |

## Boundary Decisions

OSS-0 preserves the classification that generic infrastructure can be swapped later, while Fabric-specific semantics remain explicit. The **cache port** is the safest first OSS-1 pilot because it has clear generic behavior and a straightforward rollback path. The **resilience port** separates dependency circuit-breaking from tenant governance, so a future OSS circuit breaker can be tested without moving quota or fairness policy into a library. The **scheduler port** creates a seam around execution behavior while avoiding premature Celery adoption.

| Candidate | OSS-1 Readiness | Notes |
|---|---|---|
| Cache adapter backed by `aiocache` | High | Best first pilot if it passes tenant keying, TTL, serialization, stampede, and deduplication parity tests. |
| Dependency circuit breaker adapter | Medium | Suitable for outbound dependency protection, but tenant fairness and quota enforcement should remain custom. |
| Celery or distributed task backend | Low | Requires additional scheduler decomposition before adoption because current logic includes product-specific orchestration semantics. |

## Known Notes

The Layer 4 broad unit gate initially failed when run with only `PYTHONPATH=src:../../packages/shared/src` because an existing test imports modules as `src.*`. Rerunning with `PYTHONPATH=.:src:../../packages/shared/src` matched the repository's existing mixed import style and passed. This was a validation-environment issue, not a product-code regression.

The Layer 3 cache-only tests required lazy API app construction in `tests/conftest.py` so cache characterization tests could collect independently from unrelated API app imports. This change is test-harness-only and does not alter runtime behavior.

## Recommended OSS-1 Entry Criteria

The next sprint should only introduce an OSS-backed implementation if it runs behind the new port and passes the same characterization suite. Promotion should require parity evidence for tenant isolation, TTL behavior, serialization shape, retry semantics, observability, failure modes, and rollback behavior.

| Gate | Required Evidence |
|---|---|
| Interface gate | OSS-backed adapter implements the same port as the legacy adapter. |
| Characterization gate | Existing OSS-0 characterization tests pass unchanged. |
| Shadow gate | Legacy and OSS-backed implementations can run in comparison mode before changing defaults. |
| Rollback gate | A feature flag or configuration switch restores the legacy adapter without data migration. |
| Promotion gate | Error rate, latency, correctness, and tenant isolation are equal or better than the legacy implementation. |
