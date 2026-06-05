# Audit Remediation Release Readiness Matrix

Generated: 2026-06-05

This matrix is the S6-9 release-readiness checklist for the 57-item audit
remediation wave. It is a readiness decision record, not a release approval.
The authoritative per-item evidence remains
`docs/governance/audit-remediation-sprint-register.md`; launch evidence remains
governed by `docs/launch/launch-blocker-register.md` and
`docs/launch/environment-dependent-evidence-matrix.md`.

## Decision

| Field | Value |
|---|---|
| Release posture | **NO-GO / external evidence required** |
| Reason | Required staging, live-service, trace, restore, and Prometheus evidence is not available in the current local environment. |
| Release-ready claim allowed | No |
| S6-9 checklist status | Complete as a no-go matrix; do not treat this as launch sign-off. |

## Open Release Blockers

| Audit item | Owner area | Current blocker | Next evidence required |
|---|---|---|---|
| S1-1 | Platform Infrastructure | Active Kubernetes context is `docker-desktop`, not staging. | Run a staging manual job from `postgres-backup` CronJob and attach job status plus logs. |
| S2-9 | Layer 6 | Static tenant tests pass, but live Layer 6 benchmark service tests fail with `httpx.ConnectError: [Errno 11001] getaddrinfo failed`. | Start or connect to the Layer 6 benchmark service and rerun live tenant/security invariant tests. |
| S5-2 | Platform Infrastructure | ArgoCD manifests pass static validation, but no real ArgoCD cluster sync or rollback evidence is attached. | Capture ArgoCD application sync/status and rollback-readiness evidence in staging or another approved environment. |
| S5-3 | Platform Infrastructure | WAL-G static wiring and dry-run evidence exist, but no real restore drill evidence is attached. | Execute non-production WAL-G restore drill and attach redacted restore proof, timing, and integrity checks. |
| S5-4 | Observability | Static OTel coverage exists, but live trace receipt tests fail because services are unavailable at `localhost:8000` and `localhost:8007`. | Run required services and collector/backend, then pass live trace receipt tests. |
| S5-6 | Observability | `promtool` is not installed on PATH. | Run `promtool check rules monitoring/prometheus/alerting/rules.yml` and attach the passing output. |

## Closed Local Readiness Gates

| Area | Evidence |
|---|---|
| Workflow consolidation | Current workflow count is below 50, workflow registry/permissions tests pass, and S6-6 is verified closed in the sprint register. |
| GitOps and recovery static readiness | `tests/gitops/test_rollouts.py` and `tests/recovery/` pass locally, but environment-dependent S5-2/S5-3 evidence remains open. |
| Documentation command map | `tests/docs/test_command_map.py` passes after current workflow references are aligned. |

## Sign-Off Rules

- Do not mark release-ready while any open blocker above remains without
  passing evidence or an explicit launch-owner waiver.
- Do not convert local static readiness into operational evidence for ArgoCD,
  WAL-G, Prometheus, Layer 6, or OTel.
- Update the sprint register with the exact command output or artifact location
  before changing any item to `verified closed`.
- Re-run this matrix after all open blockers have evidence attached.
