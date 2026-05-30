# Rollback Production Release Runbook

## Scope

Use this runbook when a production release must be reverted because of health-check failures, customer-visible regression, performance degradation, data-integrity concern, or security issue. It is based on the existing deployment rollback and rollout guidance.

## Severity

- **SEV2:** Post-deploy regression affects a major feature or production layer but has a safe workaround or bounded impact.
- **SEV1:** Rollback is required because of complete outage, tenant data exposure, data corruption, credential leak, or security breach.
- **SEV3:** Minor regression with limited impact and no data or security concern.

## Immediate Actions

1. Declare or join the active incident when customer impact exists.
2. Freeze further deploys for the affected services except the approved rollback.
3. Preserve deployment evidence before undoing changes: rollout history, pod logs, events, image digests, and dashboards.
4. Identify the last known-good revision or image digest and confirm it is compatible with the current database/schema state.
5. If migrations ran, confirm whether the safe action is rollback, roll-forward hotfix, feature disablement, or database recovery.
6. Execute rollback for the smallest affected service set first unless a coordinated rollback is required.
7. Validate service health and customer-critical workflows before closing the rollback.

## Procedure

```bash
# 1. Capture rollout history and current image.
kubectl rollout history deployment/<service> -n prod
kubectl get deployment/<service> -n prod -o jsonpath='{.spec.template.spec.containers[*].image}'

# 2. Roll back to a known-good Kubernetes revision.
kubectl rollout undo deployment/<service> -n prod --to-revision=<revision>

# 3. Wait for rollback completion.
kubectl rollout status deployment/<service> -n prod --timeout=300s

# 4. Verify pods and logs.
kubectl get pods -n prod -l app=<service> -o wide
kubectl logs -n prod -l app=<service> --tail=100
```

If the deployment is pinned by digest in Kustomize instead of using rollout history, revert the image digest to the last known-good value, apply the manifest, and monitor rollout status.

## Validation

- Affected deployments are available and serving the last known-good image/revision.
- Health checks pass for affected services and the API gateway.
- Error rate, latency, queue depth, and resource saturation returned to pre-release levels.
- No new tenant-isolation, audit-write, or security alerts are firing.
- If a migration was involved, application compatibility with the current schema is verified or a database runbook is active.
- Incident or release channel records the rollback reason, revision, image digest, and validation evidence.

## Evidence to Preserve

- Original release SHA, image digest, deployment revision, and manifest diff.
- Rollback command output and rollout history before/after.
- Logs and events from failed pods before termination where possible.
- Dashboard screenshots for error rate, latency, saturation, and business-critical workflow health.
- Decision record explaining why rollback was chosen over roll-forward.

## Related Gates

- `python3 scripts/ci/k8s_preflight.py`
- `make test-backend-integrated-release-smoke`
- `make check-migration-heads`
- `make verify`
- `pnpm run verify:frontend`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Deploy Production Release](deploy-production-release.md)
- [Failed Deployment](failed-deployment.md)
- [Failed Migration](../database/failed-migration.md)
- [Restore Postgres From Backup](../database/restore-postgres-from-backup.md)
- [Respond to Tenant Data Exposure](../security/respond-to-tenant-data-exposure.md)
