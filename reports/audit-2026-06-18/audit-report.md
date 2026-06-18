# Enterprise Production-Readiness Audit Report

**Date:** 2026-06-18T12:36:03.831514+00:00
**Repository:** C:\Users\BBB\Fabric_4L
**Scope:** Initial discovery audit — dependency vulnerabilities, static analysis, lint, type-check, dead code.

## Executive Summary

| Scan | Result | Notes |
| ---- | ------ | ----- |
| `pnpm audit` | FAIL (3 high, 11 moderate, 6 low) | 17 advisories; see details below |
| `make lint` | FAIL | 2 fixable UP037 errors in `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` |
| `make typecheck` | PASS | All layers type-check cleanly |
| `semgrep` | FAIL (411 results, 24 errors) | Automated SAST findings across services/apps/packages |
| `pip-audit` | FAIL (29 vulnerabilities) | Python dependency vulnerabilities; see top issues below |
| `bandit` | FAIL (5 findings) | 5 medium, 0 high severity |
| `gitleaks` | NOT RUN | Binary not installed in local environment |
| `trivy` | NOT RUN | Binary not installed in local environment |
| SBOM (CycloneDX) | PASS | Generated `artifacts/supply-chain/fabric-4l-source-sbom.cdx.json` (35 components) |
| Dead-code scan | PASS | 7 high/medium candidates already removed; 3 low-confidence candidates remain (test-referenced) |

## P0 Blockers

1. **Layer 1 lint failures** — `source_routes.py` contains forward-referenced type annotations that break ruff.
2. **Dependency vulnerabilities** — pnpm audit reports high-severity packages in the frontend dependency tree.
3. **Semgrep SAST findings** — 411 results must be triaged and classified.
4. **Bandit medium findings** — Python security patterns require review and suppression or remediation.
5. **Missing secret scanner** — `gitleaks` is not installed locally; CI already runs it, but local verification is blocked.

## P1 Items

1. **Trivy container/filesystem scan** — Not installed locally; CI runs it, but local verification is blocked.
2. **Dead code** — Remaining 3 low-confidence Layer 4 tool modules need ownership review.
3. **SLOs documentation** — Exit criteria require `docs/slo.md`; currently missing.
4. **DR runbooks** — Exit criteria require runbooks; some exist in `ops/`, need completeness review.

## Tool Details

### pnpm audit (high/moderate advisories)

| Advisory | Module | Severity | Title |
| -------- | ------ | -------- | ----- |
| GHSA-w5hq-g745-h8pq | `uuid` | moderate | uuid: Missing buffer bounds check in v3/v5/v6 when buf is provided |
| GHSA-q8mj-m7cp-5q26 | `qs` | moderate | qs has a remotely triggerable DoS: qs.stringify crashes with TypeError on null/u |
| GHSA-8x6r-g9mw-2r78 | `react-router` | high | React Router vulnerable to DoS via unbounded path expansion in __manifest endpoi |
| GHSA-ph9p-34f9-6g65 | `tmp` | high | tmp has Path Traversal via unsanitized prefix/postfix that enables directory esc |
| GHSA-hmw2-7cc7-3qxx | `form-data` | high | form-data: CRLF injection in form-data via unescaped multipart field names and f |
| GHSA-h67p-54hq-rp68 | `js-yaml` | moderate | JS-YAML: Quadratic-complexity DoS in merge key handling via repeated aliases |
| GHSA-76mc-f452-cxcm | `dompurify` | moderate | DOMPurify: Hook mutation of `data.allowedTags` / `data.allowedAttributes` perman |
| GHSA-hpcv-96wg-7vj8 | `dompurify` | moderate | DOMPurify: Cross-realm IN_PLACE sanitization leaves executable markup intact via |
| GHSA-r47g-fvhr-h676 | `dompurify` | moderate | DOMPurify: IN_PLACE mode preserves attributes of a clobbered root element, allow |
| GHSA-rp9w-3fw7-7cwq | `dompurify` | moderate | DOMPurify IN_PLACE Sanitization Bypass via Attached Shadow Root Inside <template |
| GHSA-8988-4f7v-96qf | `@opentelemetry/core` | moderate | OpenTelemetry Core: Unbounded memory allocation in W3C Baggage propagation |

### semgrep top rules

| Rule | Count |
| ---- | ----- |
| `python.lang.security.audit.formatted-sql-query.formatted-sql-query` | 158 |
| `python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query` | 158 |
| `python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure` | 34 |
| `python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text` | 13 |
| `javascript.lang.security.audit.detect-non-literal-regexp.detect-non-literal-regexp` | 8 |
| `yaml.docker-compose.security.no-new-privileges.no-new-privileges` | 5 |
| `yaml.docker-compose.security.writable-filesystem-service.writable-filesystem-service` | 5 |
| `python.lang.security.audit.non-literal-import.non-literal-import` | 5 |
| `javascript.lang.security.audit.path-traversal.path-join-resolve-traversal.path-join-resolve-traversal` | 4 |
| `javascript.lang.security.detect-child-process.detect-child-process` | 4 |

### bandit medium findings (top 10)

| File | Line | Test | Issue |
| ---- | ---- | ---- | ----- |
| `services\layer1-ingestion\migrations\versions\008_add_gin_indexes_for_jsonb.py` | 39 | `B608` | Possible SQL injection vector through string-based query con |
| `services\layer3-knowledge\tests\test_config.py` | 38 | `B104` | Possible binding to all interfaces. |
| `services\layer4-agents\migrations\versions\037_tenant_scoped_billing_customer_keys.py` | 33 | `B608` | Possible SQL injection vector through string-based query con |
| `services\layer6-benchmarks\tests\conftest.py` | 12 | `B104` | Possible binding to all interfaces. |
| `services\layer6-benchmarks\tests\test_settings_validation.py` | 35 | `B104` | Possible binding to all interfaces. |

### pip-audit top findings (top 10)

| Package | Version | ID | Fix versions |
| ------- | ------- | -- | ------------ |
| `aiohttp` | 3.13.5 | CVE-2026-34993 | ['3.14.0'] |
| `aiohttp` | 3.13.5 | CVE-2026-47265 | ['3.14.0'] |
| `aiohttp` | 3.13.5 | CVE-2026-54273 | ['3.14.1'] |
| `aiohttp` | 3.13.5 | CVE-2026-54279 | ['3.14.1'] |
| `aiohttp` | 3.13.5 | CVE-2026-54277 | ['3.14.1'] |
| `aiohttp` | 3.13.5 | CVE-2026-50269 | ['3.14.0'] |
| `aiohttp` | 3.13.5 | CVE-2026-54276 | ['3.14.1'] |
| `aiohttp` | 3.13.5 | CVE-2026-54278 | ['3.14.1'] |
| `aiohttp` | 3.13.5 | CVE-2026-54280 | ['3.14.1'] |
| `aiohttp` | 3.13.5 | CVE-2026-54274 | ['3.14.1'] |

## Dead Code

- **Existing candidates (3):** `services/layer4-agents/src/layer4_agents/tools/files.py, services/layer4-agents/src/layer4_agents/tools/admin.py, services/layer4-agents/src/layer4_agents/tools/knowledge.py`
- **Already removed (7):** `apps/web/src/pages/hypothesis/HypothesisTab.tsx, apps/web/src/pages/studio/StudioCompetitiveTab.tsx, apps/web/src/pages/studio/StudioEnrichmentTab.tsx, apps/web/src/pages/studio/StudioEvidenceTab.tsx, apps/web/src/pages/studio/StudioROITab.tsx, services/layer4-agents/src/layer4_agents/tools/analytics.py, services/layer4-agents/src/layer4_agents/tools/workflows.py`

## Artifacts

All raw JSON/TXT outputs are in `reports/audit-2026-06-18/`:
- `pnpm-audit.json` — full pnpm audit JSON
- `semgrep.json` — full Semgrep findings
- `bandit.json` — full Bandit findings
- `pip-audit.json` — full pip-audit findings
- `dead-code.json` — dead-code candidates
- `make-lint.txt` — ruff lint output
- `make-typecheck.txt` — mypy output
- `pnpm-run-sbom.txt` — SBOM generation log
- `pnpm-run-audit:ci.txt` — supply-chain CI policy log

## Next Steps

1. Fix the Layer 1 lint/typecheck issues in `source_routes.py`.
2. Triage and remediate the 3 high-severity pnpm audit advisories.
3. Triage the 411 Semgrep findings against the security baseline.
4. Review and suppress or remediate Bandit medium findings.
5. Install `gitleaks` and `trivy` locally for full parity with CI security gates.
6. Create `docs/slo.md` with SLOs and alerting rules.
