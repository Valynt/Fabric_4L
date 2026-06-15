# Environment-Dependent Evidence Matrix

This matrix prevents the repository from overclaiming launch readiness. Each row below requires a correctly configured staging, provider sandbox, or production-like launch environment. Until that evidence is attached, the status remains **REQUIRES_ENVIRONMENT**.

## Required Environment Gates

| Environment Gate | Status | Owner | Required Evidence | Minimum Acceptance Standard | Evidence Location |
|---|---|---|---|---|---|
| Production-like E2E launch rehearsal | REQUIRES_ENVIRONMENT | Test owner | Browser-executed rehearsal against the release candidate with real authentication, backing stores, persisted state, logs, and screenshots or transcript. | Critical launch journey completes without manual database intervention; failures are classified P0/P1/P2 in the blocker register. | Local surrogate evidence in `signoff-evidence/p0-journeys-20260613.json` shows the candidate is re-testable (auth crash fixed, route drift remains). Staging evidence still required. |
| Enterprise SSO/OIDC provider validation | REQUIRES_ENVIRONMENT | Identity owner | Provider metadata, redirect URI validation, login/logout proof, failed-login behavior, role/group mapping, and redacted audit event. | Authentication fails closed, maps expected tenant roles, and produces auditable events without exposing secrets. | Local Keycloak surrogate evidence in `signoff-evidence/p0-sso-20260613.json` validates OIDC wiring and claim shape. Enterprise IdP evidence still required. |
| Notification and alert receiver validation | REQUIRES_ENVIRONMENT | SRE owner | Provider test delivery, alert receiver proof, escalation route, and acknowledgement record. | Primary and backup receiver paths deliver within the approved response window. | Attach alert transcript or incident-management test record. |
| Telemetry dashboard and alert validation | REQUIRES_ENVIRONMENT | Observability owner | Dashboard links, metric/log/trace sample, alert rule proof, threshold rationale, and redaction sample. | Launch-critical service health and error budget signals are visible and alerting. | Attach dashboard URLs and redacted samples. |
| Billing and metering provider validation | REQUIRES_ENVIRONMENT | Billing owner | Meter event sample, idempotency proof, reconciliation check, invoice/usage aggregation sample, and owner sign-off. | Usage events are recorded once, reconciled, and recoverable after retry. | Attach provider sandbox or live-provider evidence. |
| Rollback and restore drill | REQUIRES_ENVIRONMENT | SRE owner | Rollback command transcript, restore proof, data-integrity check, timing result, and approval record. | Rollback and restore meet the release recovery target and leave no unreconciled data changes. | Local drill evidence in `signoff-evidence/p0-rollback-20260613.json` documents the viable rollback doctrine. Production-like rehearsal still required. |
| Performance and reliability smoke test | REQUIRES_ENVIRONMENT | Performance owner | Smoke-test command, environment shape, release-candidate SHA, latency/error-rate output, and saturation notes. | Launch-critical paths meet approved thresholds or receive explicit launch-owner waiver. | Attach performance artifact bundle. |

## Evidence Handling Rules

Evidence must be attached as redacted artifacts or links controlled by the release team. Raw provider secrets, bearer tokens, private keys, production database contents, or customer personal data must not be copied into repository documents. If evidence is unavailable, the owner must leave the row as **REQUIRES_ENVIRONMENT** and update the blocker register with the launch decision.

## Go/No-Go Interpretation

| Evidence State | Interpretation | Required Action |
|---|---|---|
| REQUIRES_ENVIRONMENT | The repository is ready for the evidence to be gathered, but live readiness is not proven. | Execute the gate in the proper environment and attach redacted evidence. |
| PASS_WITH_EVIDENCE | The gate passed and evidence is attached outside this repository or in an approved redacted artifact. | Record evidence location and owner sign-off. |
| FAIL | The gate failed in a real environment. | Open or update the P0/P1 blocker and stop launch progression until resolved. |
| WAIVED | A named launch owner accepted the risk with scope, expiration, monitoring, and rollback details. | Keep waiver attached to release decision record. |
