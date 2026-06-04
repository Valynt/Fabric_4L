# Performance, Load, and Capacity Budget Suite

This suite defines Value Fabric's safe operating envelope for CI and pre-production:
API latency, expensive-query limits, queue throughput, file upload limits, report
generation limits, and background-job backpressure.

The Python tests are deterministic guardrails and do not require live services. The
k6 profiles are the pre-production load tests and require a running stack plus
authenticated performance-test credentials.

## Fast CI Budget Tests

```bash
pytest tests/performance/
pnpm test:performance
```

Covered files:

| File | Budget area |
| --- | --- |
| `test_api_latency_budget.py` | Critical endpoint p95/error budgets and k6 threshold alignment |
| `test_expensive_queries.py` | Query shape and explicit limits for known expensive graph/formula operations |
| `test_queue_throughput.py` | Queue throughput, backlog growth, and drain-time envelope |
| `test_file_upload_limits.py` | Upload size, batch, extension, and parse-time limits |
| `test_report_generation_limits.py` | Report section/page/export time budgets |
| `test_background_job_backpressure.py` | Worker concurrency, retry, and queue-depth backpressure behavior |

## Pre-Production Load Profiles

```bash
pnpm loadtest:smoke
```

The smoke profile runs `tests/performance/k6/l2_l3_l4_critical_paths.js` for 30s and
writes `artifacts/performance/loadtest-smoke-summary.json`.

Longer profiles:

```bash
k6 run --summary-export artifacts/performance/k6-summary.json tests/performance/k6/l2_l3_l4_critical_paths.js
k6 run --summary-export artifacts/performance/stress-summary.json tests/performance/k6/stress-test.js
k6 run --summary-export artifacts/performance/spike-summary.json tests/performance/k6/spike-test.js
k6 run --summary-export artifacts/performance/soak-summary.json tests/performance/k6/soak-test.js
k6 run --summary-export artifacts/performance/workflow-summary.json tests/performance/k6/workflow-execution.js
```

Required k6 environment:

| Variable | Purpose |
| --- | --- |
| `PERF_TENANT_ID` | Tenant used for load-test traffic |
| `PERF_AUTH_BEARER` | User JWT for tenant-scoped API calls |
| `PERF_S2S_BEARER` | Service JWT for service-to-service calls |
| `L2_URL`, `L3_URL`, `L4_URL` | Layer endpoints, defaulting to localhost ports |
| `PERF_DURATION` | Profile duration, default varies by script |

## SLO and Trend Artifacts

CI evaluates `artifacts/performance/k6-summary.json` against
`docs/slo/performance-slo.v1.json` and publishes:

- `artifacts/performance/k6-summary.json`
- `artifacts/performance/slo-evaluation.json`
- `artifacts/performance/slo-window-history.json`
- `artifacts/performance/slo-report.md`

The trend artifact is intentionally machine-readable so regression dashboards can
compare p95 latency, error rate, and burn-rate windows over time.
