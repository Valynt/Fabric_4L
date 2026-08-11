# Packet (f) — Production Authority Brief: v1.0.0 Rollout & Rollback

- **Release:** Fabric_4L v1.0.0
- **Candidate ref (main):** `e3ace52032f8c80436e46adee4fba27402ae9f31`
- **Audience:** Production Authority (single human approver per `release/v1/launch-contract.yaml` `agent_topology.production_authority`)
- **Status:** awaiting signature — see approval block at bottom.

---

## 1. Rollout steps (execution order)

**Pre-deploy gates (all in-repo):**

1. `make verify` → `make production-readiness-gate` (canonical gate hierarchy, `release/v1/launch-contract.yaml:286-295`). Also: `make check-behavior-readiness-audit`, `make db-production-readiness-gate`, `make check-migration-heads`, `make check-migration-rollback-policy`, `make check-migration-postgres-roundtrip`, `make test-backup-drills`, `make test-backend-integrated-release-smoke`.
2. Run the "Prod Readiness Gates" workflow (`.github/workflows/prod-readiness.yml`) and confirm it produces a matching release packet — `.github/workflows/deploy.yml:283-289` hard-blocks any production deploy where `prod_readiness_verified != true`.
3. Confirm images exist and are signed for all 7 services (`layer1-ingestion` … `layer6-benchmarks`, `frontend`) in `ghcr.io/bmsull560/fabric_4l/`. Build pipeline is `.github/workflows/build-deploy.yml` (publishes `sha-<8>` tags — see hazard H2; deploy by **sha256 digest** or a signed semver tag).

**Deploy (canonical path = `.github/workflows/deploy.yml`, `workflow_dispatch`):**

4. Dispatch `deploy.yml` with `environment=production`, `image_ref=<sha256 digest of the certified build>`, `prod_readiness_verified=true`.
5. `preflight` job runs automatically: cosign signature verification on all 7 images, SBOM/digest cross-check against `scan-*-<sha>` artifacts, environment health checks, and deploy-profile controls via `scripts/ci/validate_deploy_profile_controls.py --policy-file .fabric/prod-gates.policy.yaml --profile release-candidate` (deploy.yml:79-289).
6. `approval-gate` job: GitHub Environment `production` protection rule — required-reviewer approval (deploy.yml:297-310).
7. `deploy` job: configures EKS kubeconfig (`value-fabric`, us-east-1), resolves overlay `k8s/overlays/production` (namespace `fabric-4l-prod`, from its `kustomization.yaml`), renders immutable digests via `scripts/ci/prepare_kustomize_deploy.sh`, `kubectl apply` + `kubectl apply -k`, then `kubectl rollout status` per deployment, 10m timeout each (deploy.yml:315-474).
8. **Database migrations:** deploy.yml contains **no migration step — no in-repo mechanism in the deploy path; manual step.** Run per-service Alembic upgrades against production before/with the rollout, scoped per `make check-migration-entrypoints` / `make check-migration-heads`; follow `docs/operations/runbooks/database-migration-rollback.md`.
9. `smoke-tests` job: `/health`, `/health/version`, `/api/v1/health` curls + `pytest tests/e2e/smoke/ --base-url=https://api.production.value-fabric.com` (deploy.yml:508-550). On failure, `rollback-on-failure` auto-runs `kubectl rollout undo` for all 7 deployments (deploy.yml:555-646).
10. `verify` + `evidence` jobs: post-deploy verification and commit of `.deployments/<date>-<tag>.md` evidence to main (deploy.yml:651-760).
11. Post-cutover observation per `docs/runbooks/deployment/deploy-production-release.md:44-51`: watch readiness, error rate, p95, queue depth, auth failures, tenant-isolation warnings.

**Alternative GitOps path:** `.github/workflows/environment-promotion.yml` (dev→staging PR→prod PR, ArgoCD). Its own header states ArgoCD cluster sync is **unverified** and the staging health loop is echo-only stubs — do not use as the v1.0.0 path without a rehearsal.

**Compose fallback:** `infra/compose/docker-compose.prod.yml` is a full-stack compose entrypoint (extends `docker-compose.full.yml`) — suitable for local prod-like rehearsal, not the EKS production deploy.

---

## 2. Rollback trigger conditions

Any one of these = stop promotion and execute `docs/runbooks/deployment/rollback-production-release.md`:

| Trigger | Threshold | Source |
|---|---|---|
| Platform-wide 5xx error rate | > 10% for 2m (`HighErrorRateCritical`, critical) | `monitoring/prometheus/alerting/rules.yml:139-153` |
| Per-layer 5xx error rate | > 5% for 5m (`HighErrorRateLayer1/2/3/4`) | `monitoring/prometheus/alerting/rules.yml:79-137` |
| Application error rate | > 0.5% sustained (launch target) | `release/v1/launch-contract.yaml:106` |
| Journey success SLO | < 99% for 10m (`JourneySuccessRateSLOViolation`, critical) | `monitoring/prometheus/alerting/rules.yml:44-53` |
| Journey empty-response | any required journey response empty for 5m (`JourneyNonEmptyResponseSLOViolation`, critical) | `monitoring/prometheus/alerting/rules.yml:66-75` |
| Journey p95 latency | > 12s for 10m (`JourneyP95LatencySLOViolation`) | `monitoring/prometheus/alerting/rules.yml:55-64` |
| API p95 latency | read > 500ms / write > 1000ms (launch targets) | `release/v1/launch-contract.yaml:103-105` |
| Tenant isolation | `WebSocketCrossTenantProbeCritical` (>20 denials/5m) or any confirmed cross-tenant access (target count 0) | `monitoring/prometheus/alerting/rules.yml:25-39`; `launch-contract.yaml:101` |
| Health/ready probes | any smoke-test or `/ready` failure post-deploy | auto-rollback: `deploy.yml:555-560` |
| Failed migration | any Alembic failure during step 8 | `docs/operations/runbooks/database-migration-rollback.md`; DB-owner approval required before any data/schema action |

Decision authority: incident commander / Production Authority decides rollback vs forward-fix (`docs/runbooks/deployment/rollback-production-release.md:7-11`).

**Rollback execution:** `kubectl rollout undo deployment/<svc> -n fabric-4l-prod` for affected/all 7 deployments (same loop as `deploy.yml:626-645`); only roll back to an **immutable image built entirely from the target commit** — see hazard H1.

---

## 3. Expand-contract rollback window

Policy source: `release/v1/launch-contract.yaml:262-280` (`migration_certification`), `release/v1/tasks/V1-MIGRATE-001.yaml`, `docs/LAUNCH_RUNBOOK.md:101`.

- **Window definition:** no fixed duration is defined in-repo. The window is open from production cutover until the Production Authority / launch owner explicitly accepts it as closed (`docs/LAUNCH_RUNBOOK.md:101`: "Keep rollback path available unless launch owner accepts that rollback window is closed").
- **Allowed during the window:**
  - Application rollback: previous application image restored against the **expanded** schema, without data loss (`launch-contract.yaml:111,274`).
  - Forward-compatible schema changes only (expand phase). Candidate code and previous image must both work against the expanded schema.
  - Backup restore as a distinct, documented recovery path (`launch-contract.yaml:279`).
- **Forbidden until the window closes:**
  - Destructive schema contraction (drops, narrowing type changes) — "destructive contraction occurs only after the rollback window" (`launch-contract.yaml:275`).
  - Unsupported Alembic downgrades: downgrades raising `NotImplemented`/`Unsupported` or marked `DOWNGRADE_UNSUPPORTED`/`restore from backup` are governed, not runnable — enforced by `scripts/ci/check_migration_rollback_policy.py` via `make check-migration-rollback-policy` (wired into `make gate-database`, Makefile:158-181). There is no customer-facing N-1 database; do not assume `alembic downgrade` is the production rollback (`launch-contract.yaml:263-264`).

---

## 4. Known hazards from evidence

- **H1 — Image-level rollback proven to crash.** `signoff-evidence/p0-rollback-20260613.json`: rollback drill FAILED — the rollback image crashed on startup with `ModuleNotFoundError: No module named 'canonical'` (`layer4_agents/services/llm_output_parser.py`); recovery to current image took 58s.
  *Mitigation:* never roll back image-only across a dependency change; roll back to an immutable image built entirely from the target commit (doctrine recorded in `docs/runbooks/deployment-rollout-and-rollback.md`); static gates `scripts/ci/verify_release_rollback.py` (8/8 PASS) and migration rollback policy PASS; rehearse a coordinated image+dependency rollback in a production-like environment before launch (drill classified RE_TESTABLE).
- **H2 — Build/deploy tag mismatch (#1257).** `.github/workflows/build-deploy.yml:82,106` publishes `sha-<8>` (`cut -c1-8`), but `.github/workflows/deploy.yml:104-109` and `environment-promotion.yml:93` reject anything that is not `sha-<40>`, semver, or `sha256:` digest — so the default build output cannot be fed to the deploy or promotion workflows.
  *Mitigation:* deploy by resolved `sha256:<64>` digest (accepted by deploy.yml), or align the tag formats before launch; do not hand-edit tags at deploy time.
- **H3 — No production deployment has ever completed.** `.deployments/` contains only `.gitkeep` and two Bunnyshell preview configs; no `<date>-<tag>.md` evidence file exists — the `evidence` job in `deploy.yml:677-760` has never run green in production.
  *Mitigation:* run the full deploy.yml path against staging first (see `signoff-evidence/gates/staging-environment-request.md`, #1257/#1260/#1261) so preflight, rollout, smoke, auto-rollback, and evidence commit are all exercised once before v1.0.0 production.
- **H4 — GitOps/canary path unverified.** `environment-promotion.yml` header states ArgoCD cluster sync unverified; its staging health loop is stubbed; `deploy-production` depends on `scripts/ci/canary_analysis.py` requiring `PROMETHEUS_URL`.
  *Mitigation:* v1.0.0 uses the direct `deploy.yml` kustomize path (steps 4-10); treat ArgoCD promotion as post-GA work.

---

## 5. Approval

By signing, the Production Authority authorizes: (a) production rollout of v1.0.0 per Section 1, (b) rollback execution per Section 2 without further approval, and (c) closure of the expand-contract rollback window only by a subsequent explicit decision.

- **Name / Role:** ______________________  (Production Authority — 1 signatory only)
- **Decision:** ☐ Approve rollout   ☐ Approve with conditions: ______________   ☐ Reject
- **Signature:** ______________________   **Date (UTC):** ______________
