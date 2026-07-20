# Audit Remediation Board

Generated: 2026-06-05

This board is the lightweight project board for the 57-item audit remediation
wave. The detailed per-item status and validation evidence remain canonical in
`docs/governance/audit-remediation-sprint-register.md`.

## Board Columns

| Column | Meaning |
|---|---|
| Backlog | Item is known but not started in the current repo. |
| In Progress | Canonical repo changes are underway or partial evidence exists. |
| Validation | Implementation exists and targeted gates are being run. |
| Blocked | A required validation or environment dependency is unavailable and recorded. |
| Verified Closed | Closure evidence is recorded in the sprint register. |

## Sprint Lanes

| Sprint | Risk label | Primary owners | Entry criteria | Exit criteria |
|---|---|---|---|---|
| Sprint 0 | P2-devex | Platform Governance, DevEx | Register exists and all 57 items are enumerated | Owner matrix, status board, severity labels, and closure rules exist |
| Sprint 1 | P0-security | Security, Layer 1, Layer 4, API Platform, DevEx | Sprint 0 artifacts exist | Security regressions and structural preflight pass or blockers are recorded |
| Sprint 2 | P0-security | Platform Security, Layers 2-6, AI Platform | Sprint 1 P0 items closed | Tenant boundary, route propagation, shim, provider, and prompt lineage gates pass |
| Sprint 3 | P0-contract | Platform Contracts, Layer 3, Billing Platform | Tenant safety gates pass | Contract drift, OpenAPI export, schema lint, and billing consolidation evidence recorded |
| Sprint 4 | P1-frontend | Frontend | Contract-sensitive backend work is stable | Frontend governance, typed-client, a11y, and design-system gates pass |
| Sprint 5 | P1-runtime | Observability, Platform Infrastructure, Frontend | Security, contract, and core frontend gates pass | Sentry, ArgoCD, WAL-G, OTel, alerts, smoke, and RUM evidence recorded |
| Sprint 6 | P2-docs | Documentation, DevEx, Architecture, AI Platform, Release | Sprints 1-5 evidence exists | Tutorials, workflow consolidation, provenance design, and release checklist complete |

## Current High-Risk Queue

| Priority | Items | Required next evidence |
|---|---|---|
| P0-contract | S3-7 | `python scripts/ci/python_contract_lint.py --strict --json` reaches zero blocking findings or an approved scoped remediation plan is recorded |
| P1-runtime | S3-4, S5-1, S5-2, S5-3, S5-4 | Runtime/service manifests, static checks, and real operational evidence where required |
| P1-frontend | S4-6, S5-8 | A11y keyboard-flow/component tests and telemetry/web-vitals evidence |
| P2-docs | S6-5, S6-8, S6-9 | Tutorial inventory, provenance persistence design, and final readiness matrix |

## Completion Checklist

> **Audit note (2026-07-18):** This completion checklist remains unchecked. The sprint register still lists S5-2/S5-3/S5-4 as `requires implementation`, which conflicts with the 2026-06-16 launch-blocker register posture of "GO WITH ACCEPTED RISKS for Core GA." Reconcile or close this checklist once the authoritative launch posture is confirmed.

- [ ] Every item in the sprint register is either `verified closed` or has an
      explicit blocker with owner and next validation.
- [ ] P0-security and P0-contract items are closed before release readiness.
- [ ] No validation command is reported as passing unless it was actually run.
- [ ] Operational items that require environment evidence include the evidence
      artifact or remain open.
- [ ] The final release readiness checklist links to the evidence rows for all
      S1-S6 items.
