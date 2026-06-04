# Crawler Capability Decision

Status: **active**

Layer 1 contains crawler functionality under `services/layer1-ingestion/src/layer1_ingestion/crawler/`, with crawler-adjacent compliance enforcement under `services/layer1-ingestion/src/layer1_ingestion/compliance/`. The audit finding for a missing `npm run test:crawler` gate is therefore resolved with an active pnpm gate rather than a non-applicability exception.

## Required gate

Run the crawler maturity gate from the repository root:

```bash
pnpm test:crawler
```

Machine-readable CI and scorecard consumers can use:

```bash
python scripts/ci/run_root_aggregate_checks.py crawler --json
```

The JSON report returns `status: pass` when the active gate passes. If the capability is ever retired or moved out of this repository, `config/ci/crawler-capability-decision.json` must be changed to `status: not_applicable` and must include the required non-applicability fields (`reason`, `owner`, `review_by`, and `scorecard_resolution`) before CI may treat the crawler mandate as satisfied.

## Gate coverage

The active crawler gate intentionally runs five coverage slices:

1. Crawler unit tests for routing, quality gates, and crawler configuration.
2. Robots, URL allowlist/SSRF, and browser-boundary policy tests.
3. Rate-limit enforcement tests.
4. Extraction-boundary tests proving crawler output is normalized before downstream use.
5. Tenant-safe ingestion propagation and hostile cross-tenant tests.

The machine-readable decision file records these required categories so the maturity scorecard can distinguish an active crawler gate from an intentional non-applicability contract.
