# Audit Remediation Owner Matrix

Generated: 2026-06-05

This owner matrix supports the June 2026 audit-remediation register in
`docs/governance/audit-remediation-sprint-register.md`. Ownership is by
platform workstream, not by individual, so each item has a durable accountable
team even before project-management assignees are added.

## Closure Policy

An item can move to `verified closed` only when the sprint register includes:

- The canonical repo change or current-state evidence.
- A targeted validation command and result.
- Any blocked validation and the exact blocker.
- Confirmation that security, tenant isolation, contracts, and governance gates
  were not weakened.

## Severity Labels

| Label | Applies to | Default response |
|---|---|---|
| P0-security | Auth, secret, SSRF, tenant isolation, fail-closed startup, cross-tenant access | Fix before frontend, docs, or polish work |
| P0-contract | Public API shape, OpenAPI export, schema drift, generated types | Run contract checks before closure |
| P1-runtime | Migration safety, deployability, backup/restore, GitOps, observability | Require static validation plus operational evidence where applicable |
| P1-frontend | Frontend governance, accessibility, typed-client usage, status components | Require typecheck and focused component/a11y tests |
| P2-docs | Tutorials, ADRs, internal links, quickstart accuracy | Require link/path validation or doc inventory evidence |
| P2-devex | Toolchain, workflow consolidation, tracking hygiene | Require command or inventory evidence |

## Owner Matrix

| Owner team | Scope | Items |
|---|---|---|
| Platform Governance | Sprint register, owner matrix, closure rules, structural preflight, release readiness | S0-1, S0-3, S1-10, S6-9 |
| DevEx | Local toolchain, package-manager policy, workflow consolidation | S0-2, S1-8, S6-6 |
| Security | Security regression suite, dev bypass removal, provider billing posture | S1-6, S1-9 |
| API Platform | Seed-data safety, privacy/API gateway contract posture | S1-4 |
| Platform Security | Tenant boundary and route propagation gates | S2-1, S2-2 |
| Layer 1 | Ingestion auth, metrics, SSRF, app-monolith legacy behavior, backup references | S1-1, S1-2, S1-5, S1-7, S1-12 |
| Layer 2 | Extraction prompt registry, provenance design, Signal Refinery documentation | S2-8, S3-3, S6-8 |
| Layer 3 | Contract drift and graph/query tenant safety | S2-3, S3-2 |
| Layer 4 | Agent tenant fallback, migration safety, provider abstraction, intent classifier | S1-3, S1-11, S2-4, S2-7, S6-7 |
| Layer 5 | Ground Truth shim integrity and tenant propagation | S2-5 |
| Layer 6 | Benchmark tenant filtering and live service validation | S2-9 |
| Billing Platform | Layer 7 billing extraction and legacy billing consolidation | S3-1, S3-4 |
| Platform Contracts | OpenAPI ingestion/export, schema required arrays, Python contract lint | S3-6, S3-7, S4-9 |
| Frontend | Design-system governance, typed wrappers, a11y, RUM/web vitals | S4-1, S4-2, S4-3, S4-4, S4-5, S4-6, S4-7, S4-8, S5-8 |
| Observability | Sentry, OpenTelemetry, Prometheus alerting | S5-1, S5-4, S5-6 |
| Platform Infrastructure | ArgoCD, WAL-G, Patroni secrets, deploy smoke | S5-2, S5-3, S5-5, S5-7 |
| AI Platform | Skill eval fixtures, provider adapters, classifier provider cleanup | S2-6, S2-7, S6-7 |
| Architecture | ADRs and layer documentation | S3-3, S6-3, S6-4 |
| Documentation | Quickstart, internal links, tutorials | S6-1, S6-2, S6-5 |

## Escalation Rules

| Condition | Escalate to |
|---|---|
| Contract check fails after OpenAPI export | Platform Contracts and affected layer owner |
| Tenant or auth gate fails | Platform Security and affected layer owner |
| Frontend typecheck or a11y gate fails | Frontend |
| Operational item lacks real environment evidence | Platform Infrastructure or Observability |
| Release checklist has any open P0/P1 item | Platform Governance |
