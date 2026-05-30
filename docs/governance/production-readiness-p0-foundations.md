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

## Canonical Makefile Gate Names

Production-readiness automation uses concise `gate-*` Makefile target names as the canonical interface. Verbose names remain only as backwards-compatible aliases and must not define independent gate behavior.

| Canonical target | Purpose | Compatibility aliases |
|---|---|---|
| `gate-policy` | Validate `.fabric/prod-gates.policy.yaml` syntax and release artifact directories. | `gates-validate-policy` |
| `gate-lint` | Run the release lint bundle across maintained Python layers. | `lint-release` |
| `gate-arch` | Run architecture conformance, tenant guard, and testability checks. | `architecture-readiness-gate` |
| `gate-security` | Run the blocking security readiness regression chain. | `security-readiness-gate` |
| `gate-tenant-isolation` | Run the dedicated launch-readiness tenant isolation suite. | None |
| `gate-security-broad` | Run advisory broad legacy security coverage. | None |
| `gate-state` | Validate frontend/backend state and workflow type alignment. | None |
| `gate-database` | Run static local database readiness checks and cross-store consistency replay. | `db-production-readiness-gate` |
| `gate-database-live` | Run live/destructive database drills requiring isolated PostgreSQL and backup environments. | None |
| `gate-chaos` | Run dependency chaos and failure-injection coverage. | None |
| `gate-smoke` | Run cross-domain smoke and golden-path verification. | None |
| `gate-agent` | Run agent provenance, behavior, and tool-boundary regression checks. | None |
| `gate-obs` | Run advisory observability, metrics, health, and SLO validation. | None |
| `gate-release-policy` | Run release policy, deprecation, and version-freeze checks. | None |
| `gate-sign-manifest` | Validate and sign the release artifact manifest. | `gates-sign-manifest` |
| `gate-summary` | Render the release summary from gate results. | `gates-render-summary` |
| `gate-production` | Run the full policy-driven production-readiness suite and collect evidence. | `production-readiness-gate` |

`.fabric/prod-gates.policy.yaml` must reference the canonical target in every `target:` field. When adding a new compatibility alias, implement it as a dependency-only alias to the canonical `gate-*` target so there is exactly one semantic implementation for each gate.


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
