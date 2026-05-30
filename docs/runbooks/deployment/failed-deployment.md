# Failed Deployment Runbook

## Scope

Use this runbook when a production deployment does not complete, stalls, fails readiness/liveness checks, hits image pull errors, or causes immediate post-deploy instability before the release is accepted.

## Severity

- **SEV2:** Deployment failure degrades production, blocks a major feature, or leaves capacity reduced.
- **SEV1:** Failed deployment causes complete outage, data integrity risk, tenant exposure, or security compromise.
- **SEV3:** Deployment failed before serving customer traffic and the previous version remains healthy.

## Immediate Actions

1. Stop promotion and freeze additional release actions for affected services.
2. Preserve rollout status, events, pod descriptions, previous logs, and rendered manifests.
3. Determine whether production traffic is still served by the previous healthy version.
4. If traffic is impacted, activate Incident Command and prepare rollback to last known-good revision.
5. Check for common deployment failures: image pull, missing secret/config, failing readiness probe, migration failure, resource quota, or node scheduling constraint.
6. If a migration failed or partially applied, switch to the failed migration runbook before retrying the deploy.
7. Communicate go/no-go: retry only after root cause is known and validation evidence is captured.

## Diagnosis

```bash
# Inspect rollout status and history.
kubectl rollout status deployment/<service> -n prod --timeout=60s
kubectl rollout history deployment/<service> -n prod

# List pods and events for the service.
kubectl get pods -n prod -l app=<service> -o wide
kubectl get events -n prod --sort-by=.lastTimestamp | tail -100

# Inspect failing pod details and previous logs.
kubectl describe pod -n prod <pod-name>
kubectl logs -n prod <pod-name> --all-containers --previous --tail=200

# Check whether required secrets/configmaps exist.
kubectl get configmaps,secrets -n prod | rg "<service>|postgres|redis|neo4j|infisical|keycloak"
```

## Validation

- Previous healthy version continues to serve traffic, or rollback completed successfully.
- No deployment is left in a partially rolled-out state without an owner and next action.
- Failing condition is identified and linked to evidence: image, config, secret, probe, migration, quota, or code regression.
- Retried deployment passes rollout status, health checks, and smoke checks.
- Release channel records whether the release was aborted, retried, rolled back, or converted to an incident.

## Evidence to Preserve

- Failed deployment SHA, image digest, manifest/Kustomize output, and CI artifact links.
- `kubectl describe` output for failing pods and deployments.
- Kubernetes events, previous container logs, probe failure messages, and image pull errors.
- Secret/config diff references without exposing secret values.
- Migration logs if database changes were part of the deploy.

## Related Gates

- `python3 scripts/ci/k8s_preflight.py`
- `make test-backend-integrated-release-smoke`
- `make check-migration-heads`
- `make verify`
- `pnpm run verify:frontend`

## Related Runbooks

- [Incident Command](../01-incident-command.md)
- [Deploy Production Release](deploy-production-release.md)
- [Rollback Production Release](rollback-production-release.md)
- [Failed Migration](../database/failed-migration.md)
- [Auth Provider Outage](../auth/auth-provider-outage.md)
- [Alert Triage](../observability/alert-triage.md)
