# Circuit Breaker Inventory — P1-014

## Date
2026-05-27

## Status
Accepted

## Context
Four separate custom circuit-breaker implementations exist across the codebase, plus ad-hoc retry logic. No shared library is used except one `tenacity` import in Layer 4's L5 client.

## Inventory

| Layer | Location | Type | Maturity | Notes |
|-------|----------|------|----------|-------|
| L1 | `src/shared/circuit_breaker.py` | Custom async CB + manager | Tested (crawler retry suite) | Tightly coupled to L1; lock held during wrapped call |
| L3 | `src/load_balancing/manager.py` | Custom sync CB | Untested | Simple counter; no async lock |
| L3 | `src/gateway/api_gateway.py` | Custom sync CB | Untested | Slightly different half-open logic |
| L4 | `src/resilience.py` | Custom async CB + registry + rate limiter | **Well tested** (510 lines) | Has protocol ports (`resilience_ports.py`) |
| L4 | `src/integration/layer5_client.py` | `tenacity` retry | Production usage | Only third-party resilience library in use |
| Shared | None | — | — | No shared CB exists today |

## Decision
Standardize on **Layer 4's circuit-breaker design** as the canonical shared pattern.

Rationale:
- Most tested implementation (`tests/test_resilience.py`).
- Already has protocol ports for substitution.
- Async-safe with state-machine semantics (CLOSED → OPEN → HALF_OPEN).
- Not tied to any external dependency.

Actions:
1. Extract a settings-agnostic `CircuitBreaker` to `packages/shared/src/value_fabric/shared/resilience/`.
2. Deprecate Layer 3 duplicate breakers in future cleanup.
3. Evaluate `tenacity` for retry-only paths separately; do not mix retry and CB abstractions yet.

## Pilot
**Layer 2.5 → Layer 3 push path** (`L3GraphClient.push_signal`).

- Breaker: `failure_threshold=3`, `recovery_timeout=30s`, `half_open_max_calls=1`
- Fallback: log warning and return `False` (best-effort, non-blocking)
- Metrics: exposed via `CircuitBreaker.get_state()` for future health probes

## Consequences
- Positive: single abstraction, consistent behavior, reusable tests.
- Negative: Layer 1 and Layer 3 custom breakers remain until migrated.
- Risk: Low — shared module is additive; no changes to existing layer implementations.
