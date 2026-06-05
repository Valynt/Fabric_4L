# Release Checklist

Use this checklist for staging and production release approvals.

## Compliance and Control Evidence

- [ ] Confirm the [Compliance Control Matrix](../compliance/control-matrix.md) has current owners, review frequency, and evidence locations.
- [ ] Attach relevant evidence links (CI run, dashboard snapshot, audit query output) to the release ticket.

## Pre-Release Validation

- [ ] Run `make verify` and confirm pass. [VERIFY:DOC-DEPLOY-001]
- [ ] Run `python scripts/ci/check_compatibility_launch_freeze.py --strict` and confirm PASS.
- [ ] Confirm every entry in `docs/governance/compatibility-debt-registry.md` includes Platform Architecture review metadata and an explicit post-launch removal ticket.
- [ ] For agent/skill changes, run `make evals` and confirm pass.
<<<<<<< ours
- [ ] Run release-smoke validation locally via `make test-backend-integrated-release-smoke` (boots the Docker L1–L6 stack; artifacts under `artifacts/release_smoke/`).
=======
- [ ] Run smoke tests (`make test-backend-integrated-release-smoke`) against the target environment.
>>>>>>> theirs
- [ ] Run `pytest tests/release/test_observability_deployment_readiness.py` and confirm PASS (release gate for Task 46/47 evidence).
- [ ] Verify `docs/readiness/observability-deployment-readiness.md` contains only `✅ PASS` rows with ISO dates and concrete artifact paths.
- [ ] Confirm CloudNativePG CRD exists: `kubectl get crd clusters.postgresql.cnpg.io`.
- [ ] Confirm Spotahome Redis Operator CRD exists: `kubectl get crd redisfailovers.databases.spotahome.com`.
- [ ] Confirm production Neo4j URI is Vault-managed Aura: `neo4j+s://...`, never `bolt://neo4j:7687`.

## Security and Operations

- [ ] Validate required secrets are set from approved secret manager (no plaintext secrets in repo).
- [ ] Confirm monitoring/alerting dashboards are healthy and on-call handoff is complete.
- [ ] Verify runbooks for active alerts are up-to-date.

## Reliability Approval (Required)

- [ ] Confirm latest `artifacts/performance/slo-report.md` and `artifacts/performance/slo-evaluation.json` are attached to the release ticket.
- [ ] Confirm SLO owner review/sign-off is recorded for impacted layers/services.

## Approval

- [ ] Release Manager sign-off.
- [ ] Security/Compliance sign-off.
- [ ] SRE sign-off.
