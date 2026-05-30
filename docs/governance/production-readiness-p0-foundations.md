# P0 Production-Readiness Foundations

The readiness assessment identified enterprise SSO/OIDC, central model management, and incident runbooks as P0 gaps. Repository inspection shows that Fabric_4L already contains substantial implementation assets for OIDC, model registry, and operational runbooks. This document turns those assets into explicit production gates so the project can distinguish **repository foundation complete** from **production evidence complete**.

## P0 Gate Matrix

| Gate | Repository foundation | Current status | Production evidence still required |
|---|---|---|---|
| Enterprise SSO/OIDC | Shared OIDC modules, Layer 4 OIDC routes and migrations, OAuth2 proxy deployment assets, and `config/production-readiness/oidc_enterprise_requirements.json`. | Foundation ready; provider evidence required. | Real provider discovery, JWKS validation, authorization-code callback, tenant mapping, logout, and audit events. |
| Model management | Layer 5 model registry models/routes/migrations, Layer 4 and Layer 2 registry clients, registry tests, and `config/production-readiness/model_governance_policy.json`. | Foundation ready; runtime evidence required. | Runtime model selection from registry, promotion/deprecation workflow, rollback drill, and audit-linked approvals. |
| Incident runbooks | Existing runbook directories plus dedicated enterprise OIDC and model registry incident runbooks. | Foundation ready; drill evidence required. | On-call drill or staging incident simulation with owner, response time, closure evidence, and post-incident review. |

## Production Assertion Rule

A P0 gate must not be marked production PASS merely because repository files exist. PASS requires a live or staging environment that exercises the relevant control with external dependencies configured, sensitive values externalized, and evidence captured without secrets.

## Canonical Makefile Production Gate Targets

Production readiness gates use concise `gate-*` Makefile targets as the canonical operator interface. Policy files, CI orchestration, and new documentation should reference these canonical names in `target:` fields and command examples.

| Canonical target | Purpose | Backwards-compatible alias |
|---|---|---|
| `gate-policy` | Gate policy schema, profile, and artifact-directory validation. | `gates-validate-policy` |
| `gate-lint` | Release lint across Python layers. | `lint-release` |
| `gate-arch` | Architecture conformance, tenant guards, and testability checks. | `architecture-readiness-gate` |
| `gate-security` | Release-critical tenant isolation, auth enforcement, and fail-closed security regression. | `security-readiness-gate` |
| `gate-security-broad` | Advisory exhaustive legacy security coverage for Broad GA backlog classification. | None |
| `gate-state` | Frontend/backend state alignment and workflow type consistency. | None |
| `gate-db-consistency` | Cross-store canonical PostgreSQL event replay into derived graph, vector, embedding, and object-store projections. | None |
| `gate-db-readiness` | Production-like database readiness across migrations, rollback, drift, tenant isolation, backup/restore, cross-store replay, credentials, and alert evidence. | `db-production-readiness-gate` |
| `gate-db-migrations` | PostgreSQL migration heads, rollback policy, and round-trip drift checks against a disposable maintenance database. | None |
| `gate-db-dr` | PostgreSQL backup/restore production-readiness drill. | None |
| `gate-chaos` | Dependency chaos and failure injection. | None |
| `gate-smoke` | Cross-domain smoke tests and golden-path verification. | None |
| `gate-agent` | Agent provenance, behavior regression, and tool-boundary checks. | None |
| `gate-obs` | Observability, metrics, health-check, and SLO validation. | None |
| `gate-release-policy` | Release policy compliance, deprecation checks, and version-freeze validation. | None |
| `gate-sign-manifest` | Release artifact manifest signing. | `gates-sign-manifest` |
| `gate-summary` | Release summary rendering. | `gates-render-summary` |
| `gate-production` | Full policy-driven production-readiness suite plus evidence collection. | `production-readiness-gate` |

Do not add new `*-readiness-gate` targets for production gates unless they are explicit aliases to a canonical `gate-*` target. Distinct database concerns must keep distinct canonical names (`gate-db-consistency`, `gate-db-readiness`, `gate-db-migrations`, or `gate-db-dr`) so similarly named targets cannot accumulate different prerequisites or recipes.


## Phase 0 Deliverable Criteria

For Layer 5 backlog governance, **"issue register complete"** means all discovered Layer 5 items are entered using `docs/governance/layer5-backlog-issue-template.md` with every required field populated:

- risk tag
- severity (P0–P3)
- owner
- due date
- affected module/path
- tenant impact
- contract impact
- rollback notes

Phase 0 must remain open if any discovered Layer 5 issue is missing required fields. In particular, missing **owner** or **due date** blocks Phase 0 closure.
