# CI Infisical OIDC Recovery and Secret Rotation

## Purpose

Recover CI secret injection and rotate affected Infisical/OIDC credentials while preserving fail-closed behavior.

## Trigger

CI jobs cannot retrieve secrets, OIDC trust failure, suspected credential exposure, failed secret rotation, or production deployment blocked by missing secrets.

## Severity

SEV-1 for suspected secret compromise or blocked emergency production fix; SEV-2 for CI/CD deployment outage; SEV-3 for non-production trust drift.

## Preconditions

Infisical admin access, GitHub OIDC configuration access, affected environment list, secret rotation owners, and rollback plan are available.

## Immediate Actions

1. Declare or confirm the incident owner and severity.
2. Freeze risky automated changes affecting the impacted service or control.
3. Capture initial timestamps, tenant/customer scope, deployment version, and active alerts.
4. Use the diagnosis steps below before applying destructive or irreversible changes.

## Diagnosis Steps

1. Confirm the trigger condition and affected environment.
2. Review the relevant dashboards, logs, audit records, and CI/readiness gate output.
3. Identify whether the issue is isolated to one tenant, service, dependency, or deployment version.
4. Preserve evidence before restarting services, rotating credentials, restoring data, or changing routing.

## Resolution Steps

1. Apply the least-risk corrective action that addresses the confirmed failure mode.
2. Keep tenant isolation, contract compatibility, and fail-closed security behavior intact.
3. Escalate to the service owner or incident commander before any destructive operation.
4. Record each operator action, command, and configuration change in the incident record.

## Validation

- Re-run the relevant health checks, smoke tests, contract checks, or readiness gates listed below.
- Confirm impacted tenants/customers can complete the critical path that failed.
- Confirm logs, metrics, and audit records show recovery and no new cross-tenant or security errors.

## Rollback / Fallback

- Prefer rollback to the last known-good deployment, configuration, registry record, backup, or credential set.
- If rollback is unsafe, isolate the impacted component, drain traffic where supported, and use the documented fallback path in the procedure details.
- Do not delete evidence or failed artifacts until the incident commander approves cleanup.

## Customer / Stakeholder Communication

- Notify the incident channel and accountable product/support stakeholders when customer impact is confirmed or likely.
- Provide scope, severity, current mitigation, expected next update time, and known customer-facing symptoms.
- Avoid sharing secrets, raw tenant data, provider tokens, or unreviewed root-cause speculation.

## Evidence to Preserve

- Alert names, timestamps, dashboard snapshots or links, and runbook version.
- Deployment SHAs, configuration diffs, migration IDs, registry versions, or backup artifact IDs.
- Sanitized logs, audit events, gate outputs, validation commands, and operator action timeline.

## Related Gates

Deployment and secret-readiness gates: CI OIDC secret-injection checks, structural-preflight, required CI checks, production safety validator gates, deployment gates after rotation, and control attestation evidence.

## Related Runbooks

- [Deployment Rollout, Canary/Blue-Green Criteria, and Rollback](../deployment-rollout-and-rollback.md)
- [Quarterly Control Attestation Runbook](../compliance/quarterly-control-attestation.md)

## Post-Incident Follow-Up

- Attach validation evidence and gate results to the incident record.
- File corrective actions for missing alerts, missing tests, stale documentation, or slow recovery steps.
- Update this runbook and related gates if the incident exposed drift or an undocumented dependency.

---

## Procedure Details

### Scope

This runbook covers CI failures caused by Infisical OIDC authentication or secret retrieval issues. CI is fail-closed: workflows must not use static fallback values for `OPENAI_API_KEY` or `JWT_SECRET`.

### Emergency secret rotation

1. Trigger `.github/workflows/api-key-rotation.yml` for `OPENAI_API_KEY` rotations.
2. Trigger `.github/workflows/secret-rotation.yml` for `JWT_SECRET` rotations.
3. Validate new values in Infisical for the required environment paths before re-running CI.
4. Re-run the failed workflow and confirm Infisical fetch steps succeed.

### CI recovery path (fail-closed)

1. Confirm GitHub Actions job has `permissions: id-token: write`.
2. Confirm `INFISICAL_IDENTITY_ID` repository secret is present and matches the machine identity.
3. Verify Infisical machine identity policy grants read access to required secret paths.
4. Validate OIDC audience and environment slug values used by `Infisical/secrets-action`.
5. Re-run job only after Infisical access is restored; do not add GitHub Secrets fallback steps.

### Post-incident checklist

- Remove temporary incident notes from workflow files.
- Confirm `scripts/ci/check_no_workflow_secret_fallbacks.py` passes.
- Link incident evidence and remediation in the PR.
