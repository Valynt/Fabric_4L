# CI Infisical OIDC Recovery and Secret Rotation

## Scope

This runbook covers CI failures caused by Infisical OIDC authentication or secret retrieval issues. CI is fail-closed: workflows must not use static fallback values for `OPENAI_API_KEY` or `JWT_SECRET`.

## Emergency secret rotation

1. Trigger `.github/workflows/api-key-rotation.yml` for `OPENAI_API_KEY` rotations.
2. Trigger `.github/workflows/secret-rotation.yml` for `JWT_SECRET` rotations.
3. Validate new values in Infisical for the required environment paths before re-running CI.
4. Re-run the failed workflow and confirm Infisical fetch steps succeed.

## CI recovery path (fail-closed)

1. Confirm GitHub Actions job has `permissions: id-token: write`.
2. Confirm `INFISICAL_IDENTITY_ID` repository secret is present and matches the machine identity.
3. Verify Infisical machine identity policy grants read access to required secret paths.
4. Validate OIDC audience and environment slug values used by `Infisical/secrets-action`.
5. Re-run job only after Infisical access is restored; do not add GitHub Secrets fallback steps.

## Post-incident checklist

- Remove temporary incident notes from workflow files.
- Confirm `scripts/ci/check_no_workflow_secret_fallbacks.py` passes.
- Link incident evidence and remediation in the PR.
