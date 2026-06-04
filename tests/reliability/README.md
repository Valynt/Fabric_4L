# Reliability Readiness Suite

## What This Suite Validates

This suite centralizes CI-safe reliability checks for health probes, SLO policy, error budget controls, retry/timeout behavior, graceful degradation, and dependency failure modes.

## Production Risks Covered

- Services that deploy without health or readiness contracts.
- SLOs, alert thresholds, or error budget policies missing from release evidence.
- Retry behavior that amplifies outages or omits timeout boundaries.
- Dependency failures that bypass tenant isolation or fabricate success.
- Degraded modes that are not explicit or auditable.

## Existing Coverage Aggregated

- `tests/contract/test_health_contract_and_red_metrics.py`
- `tests/contract/test_service_observability_contracts.py`
- `tests/backend_integrated/test_layer_health_checks.py`
- `tests/chaos/`
- `tests/ci/test_perf_slo_baseline.py`
- `tests/ci/test_stack_health_check_contract.py`

## Known Gaps

- LIVE_SLO_EVIDENCE: this suite validates SLO definitions and CI gates; real production burn-rate evidence must come from monitoring artifacts.
- LIVE_DEPENDENCY_CHAOS: destructive chaos drills remain in scheduled or manual workflows, not PR-local pytest.

## How To Run

```bash
pytest tests/reliability/
pnpm test:reliability
```

## CI Artifact

CI should publish `artifacts/production-readiness/reliability/junit.xml` and `artifacts/production-readiness/reliability/summary.md`.

