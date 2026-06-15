# Accepted Risk Waivers — 2026-06-15

- **Authority:** Release Management / Product / Security / Operations
- **Effective date (UTC):** 2026-06-15
- **Expiration date (UTC):** 2026-07-15 unless rescinded earlier by evidence attachment
- **Related artifacts:**
  - `docs/readiness/current.md`
  - `docs/readiness/launch-decision-artifact.md`
  - `docs/launch/launch-blocker-register.md`
  - `production-readiness/scorecard.md`
  - `production-readiness/risk_register.md`

## Waiver policy

These waivers apply only to **environment-dependent** or **provider-dependent** launch evidence that cannot be produced from the repository alone. They do **not** excuse repository-owned code defects, tenant-isolation failures, auth bypasses, or unvalidated contract drift.

A waiver is active only after all required owner signatures are present. Until signed, the affected item remains an open blocker.

---

## WVR-2026-06-15-001 — P0 Playwright launch-journey evidence

| Field | Value |
|---|---|
| **Tracked blocker** | `docs/launch/launch-blocker-register.md` P0-001 |
| **Risk register item** | `production-readiness/risk_register.md` PRR-003, PRR-010 |
| **Owner** | Test owner |
| **Approving owner** | _TBD_ |
| **Customer impact statement** | Launch may proceed without retained staging evidence for all 7 P0 Playwright journeys. The repository-owned route drift in `j1` and `j20` specs has been fixed (`/settings/*` → `/t/:tenantSlug/settings/*`) and `apps/web` typecheck passes. The local critical-path smoke (`12/0` passed) and backend contract tests cover the same functional paths; residual risk is limited to UI-level selector drift and auth-provider configuration not exercised locally. |
| **Scope reduction** | None. Core GA still requires at least the canonical J1 backend-integrated path to be validated in staging before the waiver expires. |
| **Rollback plan** | If journey-level defects are detected post-launch, revert the tenant-scoped route change or patch the affected frontend route contract; rollback follows `docs/runbooks/deployment-rollout-and-rollback.md`. |
| **Monitoring plan** | Frontend error-tracking and journey SLO alerts must be operational in staging/production; any P0 journey failure in the first 7 days triggers a launch review. |
| **Expiry condition** | Attach retained staging JUnit/trace evidence for all 7 P0 journeys, or renew the waiver with executive approval. |

**Signatures**

| Function | Name | Date |
|---|---|---|
| Engineering owner | | |
| Security owner | | |
| Product owner | | |
| Operations owner | | |

---

## WVR-2026-06-15-002 — P0 runtime rollback/restore rehearsal

| Field | Value |
|---|---|
| **Tracked blocker** | `docs/launch/launch-blocker-register.md` P0-002 |
| **Risk register item** | `production-readiness/risk_register.md` PRR-004, PRR-010 |
| **Owner** | SRE owner |
| **Approving owner** | _TBD_ |
| **Customer impact statement** | Launch may proceed without a production-like rollback rehearsal. Static rollback verification (`8/8` passed), backup cronjobs, restore dry-run, and documented immutable-image doctrine provide a defensible recovery baseline. Residual risk is a longer-than-target recovery time if a coordinated source+dependency rollback is required. |
| **Scope reduction** | None. Rollback capability is still required; this waiver only defers the live rehearsal. |
| **Rollback plan** | Use immutable, commit-pinned images or coordinated source+dependency rollback per `docs/runbooks/deployment-rollout-and-rollback.md`; maintain `rollback-target` image tag. |
| **Monitoring plan** | Post-deploy smoke checks and SLO burn-rate alerts trigger automatic traffic switch-back; incident response follows the deployment runbook. |
| **Expiry condition** | Complete and attach a production-like rollback rehearsal transcript, or renew the waiver with executive approval. |

**Signatures**

| Function | Name | Date |
|---|---|---|
| Engineering owner | | |
| Security owner | | |
| Product owner | | |
| Operations owner | | |

---

## WVR-2026-06-15-003 — P0 enterprise SSO/OIDC provider validation

| Field | Value |
|---|---|
| **Tracked blocker** | `docs/launch/launch-blocker-register.md` P0-003 |
| **Risk register item** | `production-readiness/risk_register.md` PRR-010 |
| **Owner** | Identity owner |
| **Approving owner** | _TBD_ |
| **Customer impact statement** | Launch may proceed without real enterprise IdP evidence. The local Keycloak surrogate (`fabric` realm, direct-access grants, `realm_access.roles` + `tenant_id` + `org_id` claims) validates the OIDC integration path. Residual risk is IdP-specific mapping/refusal behavior not exercised against a production-like provider. |
| **Scope reduction** | None. Enterprise SSO remains required for paid/enterprise launch; this waiver defers provider-specific validation. |
| **Rollback plan** | If SSO issues occur, disable the enterprise IdP route and fall back to Clerk-managed authentication; auth fail-closed behavior is preserved. |
| **Monitoring plan** | Auth failure rate, token validation errors, and identity-webhook delivery are monitored; provider integration is validated in staging before the waiver expires. |
| **Expiry condition** | Attach enterprise IdP login/logout/role-mapping audit evidence, or renew the waiver with executive approval. |

**Signatures**

| Function | Name | Date |
|---|---|---|
| Engineering owner | | |
| Security owner | | |
| Product owner | | |
| Operations owner | | |

---

## WVR-2026-06-15-004 — Tenant-isolation aggregate gate (infra-blocked)

| Field | Value |
|---|---|
| **Tracked blocker** | `production-readiness/risk_register.md` PRR-002 |
| **Owner** | Platform Security |
| **Approving owner** | _TBD_ |
| **Customer impact statement** | The `pnpm test:isolation` aggregate gate cannot complete in the current environment because Redis is not reachable on `localhost:6379`; this is an infrastructure limitation, not a code regression. Historical hostile cross-tenant tests (`49/49` passed), security smoke tenant-isolation tests, and behavior-readiness route-auth dependencies provide isolation confidence. |
| **Scope reduction** | None. Tenant isolation remains a non-negotiable invariant. |
| **Rollback plan** | If a tenant-isolation regression is detected, immediately freeze rollout and revert the offending change; invoke the tenant-isolation incident runbook. |
| **Monitoring plan** | CI must run the full `pnpm test:isolation` aggregate in an environment with Redis/Neo4j before the waiver expires; security smoke and hostile cross-tenant suites run on every PR. |
| **Expiry condition** | Re-run `pnpm test:isolation` in a configured CI environment and attach passing evidence, or renew the waiver with executive approval. |

**Signatures**

| Function | Name | Date |
|---|---|---|
| Engineering owner | | |
| Security owner | | |
| Product owner | | |
| Operations owner | | |

---

## WVR-2026-06-15-005 — P1 observability dashboards and alert receivers

| Field | Value |
|---|---|
| **Tracked blocker** | `production-readiness/risk_register.md` PRR-006 |
| **Owner** | SRE / Observability owner |
| **Approving owner** | _TBD_ |
| **Customer impact statement** | Launch may proceed without live dashboards and alert-receiver evidence. Metrics endpoints are reachable on L4/L5/L6; `pnpm lint:logs` and observability contract tests pass. Residual risk is slower incident detection/response until dashboards and paging are validated. |
| **Scope reduction** | None. Observability is required for production support; this waiver defers dashboard/receiver validation. |
| **Rollback plan** | Manual log/metrics inspection via existing endpoints until dashboards are operational. |
| **Monitoring plan** | Deploy Prometheus/Grafana/Alertmanager before go-live; validate alert receivers within 48 hours of launch. |
| **Expiry condition** | Attach dashboard links, alert-rule evidence, and receiver test receipts, or renew the waiver with executive approval. |

**Signatures**

| Function | Name | Date |
|---|---|---|
| Engineering owner | | |
| Security owner | | |
| Product owner | | |
| Operations owner | | |

---

## WVR-2026-06-15-006 — P1 billing and metering provider validation

| Field | Value |
|---|---|
| **Tracked blocker** | `production-readiness/risk_register.md` PRR-007 |
| **Owner** | Billing owner |
| **Approving owner** | _TBD_ |
| **Customer impact statement** | Launch may proceed without live billing-provider integration evidence. Local billing regression tests (`17/17` passed) cover subscription lifecycle, entitlement sync, webhook idempotency, and cancellation behavior. Residual risk is provider-specific metering/reconciliation defects for paid GA. |
| **Scope reduction** | If Core GA is **unpaid**, billing may be formally scoped out of launch; if paid GA is intended, this waiver defers provider validation only. |
| **Rollback plan** | If billing defects occur, disable paid-feature gates and grandfather existing customers until reconciliation is fixed. |
| **Monitoring plan** | Billing webhook delivery, meter event volume, and invoice reconciliation are monitored; provider sandbox validation is completed before the waiver expires. |
| **Expiry condition** | Attach live/sandbox provider evidence (meter events, invoice sample, idempotency check), or renew the waiver with executive approval. |

**Signatures**

| Function | Name | Date |
|---|---|---|
| Engineering owner | | |
| Security owner | | |
| Product owner | | |
| Operations owner | | |

---

## WVR-2026-06-15-007 — P1 compliance evidence owner sign-off

| Field | Value |
|---|---|
| **Tracked blocker** | `production-readiness/risk_register.md` PRR-008 |
| **Owner** | Compliance owner |
| **Approving owner** | _TBD_ |
| **Customer impact statement** | Launch may proceed without formal SOC2/ISO control-owner sign-off. Audit and config evidence tests (`212` total passed) demonstrate that controls are documented and wired into CI. Residual risk is audit-readiness gaps identified in a future control review. |
| **Scope reduction** | None. Compliance remains required; this waiver defers formal owner attestation. |
| **Rollback plan** | If audit gaps are identified, implement remediation plan and schedule re-attestation. |
| **Monitoring plan** | Compliance owner reviews evidence retention location and control ownership within 14 days of launch. |
| **Expiry condition** | Compliance owner signs off and records retained evidence location, or renews the waiver with executive approval. |

**Signatures**

| Function | Name | Date |
|---|---|---|
| Engineering owner | | |
| Security owner | | |
| Product owner | | |
| Operations owner | | |

---

## Waiver activation rule

No waiver is active until **all four** function owners have signed the corresponding signature block. A missing signature is treated as an open blocker and voids the `GO WITH ACCEPTED RISKS` posture for the affected item.
