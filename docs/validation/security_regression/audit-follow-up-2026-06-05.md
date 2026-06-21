# Audit Follow-Up Security Evidence - 2026-06-05

This note records the repeatable validation for the fresh-audit follow-up backlog. It is scoped to L1 metrics access, L1 SSRF guard behavior, frontend console cleanup, production JWT safety, root security aggregation, and root hostile tenant coverage.

> Historical note: the `corepack pnpm test:security` command was removed from `package.json` after this run. The current canonical security gate is `make gate-security`; hostile tenant tests are run via `corepack pnpm test:security:hostile`. The command table below is preserved as a record of the 2026-06-05 run.

## Commands Run

| Area | Command | Result |
| --- | --- | --- |
| Package script parse | `python -c "import json; json.load(open('package.json', encoding='utf-8')); print('package json ok')"` | Passed: `package json ok` |
| L1 metrics and SSRF focused tests | `python -m pytest tests/security/test_l1_metrics_access.py tests/security/test_l1_ssrf_blocklist.py -v --tb=short` | Passed: `21 passed, 21 warnings` |
| Manifest references for new evidence | `python -m pytest tests/security/test_auth_guards.py tests/security/test_secret_handling.py tests/security/test_tenant_isolation.py -v --tb=short` | Passed with live-infra skips: `7 passed, 9 skipped, 16 warnings` |
| Root hostile tenant command | `corepack pnpm test:security:hostile` | Passed: `15 passed, 15 warnings` |
| Root security CI entrypoint | `corepack pnpm test:security` | Passed: `6 passed, 9 deselected, 6 warnings` |
| Production JWT placeholder safety | `python -m pytest packages/shared/src/value_fabric/shared/security/tests/test_production_safety.py::TestProductionSafetyMatrix::test_placeholder_jwt_secret_fails_in_production_like -v --tb=short` | Passed: `3 passed` |
| Environment-matrix JWT placeholder safety | `python -m pytest tests/config/test_environment_matrix.py -k auth_placeholder_jwt_secret -v --tb=short` | Passed: `3 passed, 109 deselected` |
| Frontend production-source console search | `rg -n "console\.(log|warn|error|info|debug)" apps/web/src -S -g "!**/*.test.ts" -g "!**/*.test.tsx" -g "!**/*.spec.ts" -g "!**/*.spec.tsx"` | Passed by absence: no production-source matches |
| Frontend lint | `corepack pnpm --dir apps/web run lint` | Passed |
| Frontend tests | `corepack pnpm --dir apps/web run test` | Passed |

## Evidence Notes

- `corepack pnpm test:security:hostile` is the cross-platform root hostile tenant command. It avoids shell-dependent expansion of `tests/security/test_hostile_*.py` on Windows.
- `make gate-security` is the current canonical security readiness gate. The historical `corepack pnpm test:security` entrypoint above ran the same six category-manifest tests that are now exercised by the gate.
- L1 `/metrics` focused coverage proves the registered L1 metrics path is inventoried, unauthenticated access fails closed, and valid metrics scrape tokens preserve Prometheus text output.
- L1 SSRF focused coverage proves cloud metadata IPs and hostnames are blocked through `layer1_ingestion.compliance.url_safety.validate_url_safety` using monkeypatched DNS resolution where hostnames are involved.
- Production JWT safety is verified directly against `validate_production_safety()` for `JWT_SECRET=changeme` in production-like environments.
- The explicit manifest-file run includes legacy live-infra tests; Redis/PostgreSQL-dependent checks were skipped because local services were unavailable. That does not affect the directory-level security aggregation result.

