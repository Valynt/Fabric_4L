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

## Canonical Production Gate Make Targets

Production-readiness automation uses concise `gate-*` Makefile targets as the canonical names. The policy file at `.fabric/prod-gates.policy.yaml` must reference only these canonical names in `gate-definitions.*.target`; legacy and verbose names remain Makefile aliases for backwards compatibility and should not be used in new policy entries, CI workflow definitions, or documentation.

| Gate definition | Canonical target | Purpose | Backwards-compatible aliases |
|---|---|---|---|
| `policy` | `gate-policy` | Validate production gate policy YAML, selected profile, and artifact directories. | `gates-validate-policy` |
| `lint` | `gate-lint` | Run release-grade Python layer linting. | `lint-release` |
| `arch` | `gate-arch` | Validate architecture conformance, tenant guards, and testability. | `architecture-readiness-gate` |
| `security` | `gate-security` | Run release-critical tenant isolation, authentication, and fail-closed security regression checks. | `security-readiness-gate` |
| `security-broad` | `gate-security-broad` | Run advisory broad legacy security coverage. | None |
| `chaos` | `gate-chaos` | Run dependency chaos and failure-injection checks. | None |
| `smoke` | `gate-smoke` | Run cross-domain smoke and golden-path checks. | None |
| `state` | `gate-state` | Validate frontend/backend state alignment and workflow type consistency. | None |
| `agent` | `gate-agent` | Run agent provenance and behavior regression checks. | None |
| `obs` | `gate-obs` | Run observability, metrics, health, and SLO validation checks. | None |
| `release-policy` | `gate-release-policy` | Validate release policy, deprecations, and version-freeze expectations. | None |
| `sign-manifest` | `gate-sign-manifest` | Sign release artifacts with SHA-256 manifest evidence. | `gates-sign-manifest` |
| `summary` | `gate-summary` | Render the release gate summary artifact. | `gates-render-summary` |
| Full sequence | `gate-production` | Run the policy-driven production-readiness gate sequence for `PROFILE`. | `release-gate`, `gate-all`, `production-readiness-gate` |

Do not create additional targets whose names imply the same gate semantics. If a historical name must keep working, implement it as a dependency-only alias of the canonical target so there is a single source of behavior.
