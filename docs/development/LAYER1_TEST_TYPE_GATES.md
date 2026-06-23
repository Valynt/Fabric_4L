# Layer 1 Test & Type Gates

This document defines the Layer 1 ingestion test lanes and mypy policy.

## Test lanes

| Lane | Command | External services | CI gate |
|------|---------|-------------------|---------|
| **Unit** | `make test-layer1` | None (no Postgres, Docker, network, or broker) | Required on every PR |
| **Integration** | `make test-layer1-integration` | PostgreSQL (port 5432) | Required before merge/release |
| **E2E / full stack** | `make test-backend-integrated-validation` | Full L1-L6 stack | Release / periodic |

Tests under `services/layer1-ingestion/tests/unit` must be runnable without any
external service. API endpoint tests that need a real database connection live in
`services/layer1-ingestion/tests/integration` and are marked with
`@pytest.mark.integration` and `@pytest.mark.postgres`.

## Markers

The `pyproject.toml` registers these markers:

- `unit`: tests that require no external services
- `integration`: tests that exercise external services or API endpoints
- `postgres`: tests that require a reachable PostgreSQL instance
- `requires_postgres`: legacy marker, also skips when PostgreSQL is unavailable

## Mypy policy

| Gate | Command | Policy | CI gate |
|------|---------|--------|---------|
| **Typed core** | `scripts/ci/check_mypy_typed_core.py` | Zero errors in `orchestrator/`, `domain/`, and `shared/models.py` | Required on every PR |
| **Changed files** | `scripts/ci/check_mypy_changed_files.py` | Zero errors on touched `.py` files under `src/` | Required on every PR |
| **Baseline ratchet** | `scripts/ci/check_mypy_baseline.py` | Total errors per file cannot exceed the checked-in baseline | Required on every PR |

Legacy debt (e.g. `app_monolith.py`) is captured in
`config/ci/mypy_baseline_layer1.json` (currently 219 errors across 4 files).
`api/source_routes.py` was removed from the baseline after its mypy error was fixed.
Each sprint should reduce the baseline; new code must not increase it.

## Regenerating the baseline

```bash
python scripts/ci/check_mypy_baseline.py \
  --service-dir services/layer1-ingestion \
  --baseline config/ci/mypy_baseline_layer1.json \
  --paths src \
  --write-baseline
```

Commit the updated baseline only when it reflects a deliberate reduction in
legacy typing debt.
