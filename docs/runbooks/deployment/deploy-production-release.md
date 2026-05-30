# Deploy Production Release Runbook

## Scope

Use this runbook for planned production releases of Value Fabric services, frontend assets, Kubernetes manifests, and release bundles. It adapts the existing deployment rollout guidance into a production release checklist with explicit validation and evidence requirements.

## Severity

- **Normal operation:** Planned release, no incident.
- **SEV2:** Release causes broad degradation, failed health checks for a production layer, or customer-visible rollback need.
- **SEV1:** Release causes data corruption, suspected tenant exposure, credential leak, complete outage, or unrecoverable data loss.

## Immediate Actions

1. Confirm the release SHA, image digests, target environment, release owner, and rollback owner.
2. Confirm change approval, maintenance window if required, and no active release freeze.
3. Verify required CI gates passed for the exact SHA being deployed.
4. Confirm database migration plan, backup status, and rollback/roll-forward decision criteria.
5. Announce deployment start in the release channel with expected checkpoints and abort criteria.
6. Apply manifests using pinned image digests only; never deploy mutable `latest` tags.
7. Watch rollout status, service health, error rate, latency, tenant-isolation alerts, and audit-write alerts until the release is stable.

## Procedure

```bash
# 1. Verify the release commit and local working tree.
git status --short
git rev-parse HEAD

# 2. Run Kubernetes manifest preflight before production apply.
python3 scripts/ci/k8s_preflight.py

# 3. Apply rendered production manifests.
kubectl apply -k k8s/deployments/prod-nginx

# 4. Monitor each deployment until complete.
kubectl rollout status deployment/<service> -n prod --timeout=300s

# 5. Inspect pods and recent logs.
kubectl get pods -n prod -o wide
kubectl logs -n prod -l app=<service> --tail=100
```

For higher-risk releases, use a staged rollout where supported: 5% traffic, 25%, 50%, then 100%, with error-rate and latency checks at each stage.

## Validation

- All expected deployments reached `Available=True` and no pods are in `CrashLoopBackOff`, `ImagePullBackOff`, or sustained `Pending` state.
- Service `/health` checks pass for affected layers and the API gateway.
- 5xx rate, p95 latency, queue depth, audit-write failures, and tenant-isolation alerts remain within normal thresholds.
- Contract-sensitive changes have matching OpenAPI, JSON Schema, generated types, UI consumers, and tests.
- Any migrations have exactly one expected Alembic head per service and application reads/writes pass smoke checks.
- Release channel includes deployed SHA, image digest, validation result, and explicit go/no-go decision.

## Evidence to Preserve

- CI run links, gate summaries, and artifact digests.
- Release approval, deploy start/end timestamps, operator, and commands run.
- Rendered manifest diff or Kustomize output for production.
- `kubectl rollout status` output, health check output, and relevant dashboard snapshots.
- Migration version before and after deployment, if applicable.

## Related Gates

- `make verify`
- `python3 scripts/ci/k8s_preflight.py`
- `make check-migration-heads`
- `make test-backend-integrated-release-smoke`
- `pnpm run check:contract-compliance`
- `pnpm run check:api-types`
- `pnpm run verify:frontend`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Rollback Production Release](rollback-production-release.md)
- [Failed Deployment](failed-deployment.md)
- [Failed Migration](../database/failed-migration.md)
- [Alert Triage](../observability/alert-triage.md)
