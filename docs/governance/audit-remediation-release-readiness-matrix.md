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
| Reason | Required staging, ArgoCD sync, trace, and restore evidence is not available in the current local environment. |
| Release-ready claim allowed | No |
| S6-9 checklist status | Complete as a no-go matrix; do not treat this as launch sign-off. |

## PASS Criteria

The matrix may move to **PASS** only when every row below has passing evidence
recorded in the sprint register or an approved launch-owner waiver linked from
the launch blocker register.

| Audit item | PASS evidence required | Current route to PASS |
|---|---|---|
| S1-1 | Staging `postgres-backup` CronJob/manual job succeeds and logs are attached. | Switch from `docker-desktop` to staging Kubernetes context, run the backup job, and attach job status plus logs. |
| S5-2 | ArgoCD app sync/status and rollback-readiness evidence pass in a real cluster. | Use staging or another approved cluster with ArgoCD installed; static manifest tests are not sufficient. |
| S5-3 | Non-production WAL-G restore drill succeeds with redacted restore proof, timing, and integrity checks. | Execute the restore drill against an approved non-production target; dry-run evidence is not sufficient. |
| S5-4 | Live trace receipt tests pass with the required services and collector/backend running. | Re-run `tests/backend_integrated/test_otel_trace_receipt.py` after billing, Layer 2.5, Layer 7, and Jaeger are reachable, or run it in staging/backend-integrated CI. |

## Open Release Blockers

| Audit item | Owner area | Current blocker | Next evidence required |
|---|---|---|---|
| S1-1 | Platform Infrastructure | Active Kubernetes context is `docker-desktop`, not staging. | Run a staging manual job from `postgres-backup` CronJob and attach job status plus logs. |
| S5-2 | Platform Infrastructure | ArgoCD manifests pass static validation, but no real ArgoCD cluster sync or rollback evidence is attached. | Capture ArgoCD application sync/status and rollback-readiness evidence in staging or another approved environment. |
| S5-3 | Platform Infrastructure | WAL-G static wiring and dry-run evidence exist, but no real restore drill evidence is attached. | Execute non-production WAL-G restore drill and attach redacted restore proof, timing, and integrity checks. |
| S5-4 | Observability | Static OTel coverage exists, but the latest local live trace retry failed because billing, Layer 2.5, and Layer 7 were not reachable on their default local ports. | Run `tests/backend_integrated/test_otel_trace_receipt.py` with `BILLING_URL`, `LAYER25_URL`, `LAYER7_URL`, and `JAEGER_URL` set against running services, then attach passing output. |

## Closed Local Readiness Gates

| Area | Evidence |
|---|---|
| Workflow consolidation | Current workflow count is below 50, workflow registry/permissions tests pass, and S6-6 is verified closed in the sprint register. |
| Layer 6 tenant isolation | `python -m pytest services/layer6-benchmarks/tests/test_repository_tenant_isolation.py services/layer6-benchmarks/tests/test_cross_tenant_hostile.py tests/security/test_benchmarks_cross_tenant_isolation.py -v --tb=short` passed 26 tests; S2-9 is verified closed in the sprint register. |
| GitOps and recovery static readiness | `tests/gitops/test_rollouts.py` and `tests/recovery/` pass locally, but environment-dependent S5-2/S5-3 evidence remains open. |
| Prometheus alert rules | `docker run --rm --entrypoint promtool -v "C:\Users\BBB\Fabric_4L\monitoring\prometheus\alerting:/rules:ro" prom/prometheus:v2.55.1 check rules /rules/rules.yml` passed with `SUCCESS: 11 rules found`; S5-6 is verified closed in the sprint register. |
| Repository-owned readiness | `corepack pnpm readiness:10` passed 10/10 locally, including schema index, router contract, CI workflow registry, evidence packet generation, and maturity scorecard threshold. |
| Documentation command map | `tests/docs/test_command_map.py` passes after current workflow references are aligned. |

## Sign-Off Rules

- Do not mark release-ready while any open blocker above remains without
  passing evidence or an explicit launch-owner waiver.
- Do not convert local static readiness into operational evidence for ArgoCD,
  WAL-G, or OTel.
- Update the sprint register with the exact command output or artifact location
  before changing any item to `verified closed`.
- Re-run this matrix after all open blockers have evidence attached.
