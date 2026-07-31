# Security Scanning Certification and Operations Guide

## Certification state

**Status: BLOCKED EXTERNALLY.** Repository-level repairs and static contract validation do not substitute for database-backed scanner execution or GitHub evidence. The checkout has no remote, `gh` and Docker are unavailable, direct GitHub API access is blocked, and local `pnpm audit` receives HTTP 403. Therefore no final PR run IDs, job IDs, required-context state, image scans, ZAP reachability, SARIF uploads, merge, or post-merge main validation can be certified here.

The machine-readable sources are [`security/scanning/tool-inventory.json`](../../security/scanning/tool-inventory.json) and [`security/scanning/consolidated-findings.json`](../../security/scanning/consolidated-findings.json). They deliberately classify unavailable evidence as blocked, never clean.

## Workflow map and command reference

| Tier | Canonical workflow | Scope | Evidence |
|---|---|---|---|
| PR/protected branch | `security-gates.yml` | SAST, history/tree secrets, Trivy repository/image/SBOM, baseline DAST, mandatory regression | SARIF plus retained reports |
| Dependency changes/schedule | `dependency-scan.yml` | per-service Python lock resolution, pnpm lock graph, Dependency Review, container dependency scan | JSON, SARIF, diagnostics |
| Source/release supply chain | `supply-chain-integrity.yml` | CycloneDX/SPDX, Grype, signatures, license/dependency controls | SBOM, SARIF, report |
| Release adapter | `sbom.yml` | invokes the canonical reusable supply-chain workflow | same canonical artifacts |
| Scheduled/manual controlled DAST | `penetration-testing.yml` | ephemeral localhost full ZAP and Nikto | JSON, XML, HTML, Markdown, SARIF |

Local static checks:

```bash
pytest --no-mandatory-dep-check -q tests/ci/test_security_scanning_certification.py tests/ci/test_penetration_testing_workflow_assets.py
python -c 'import pathlib,yaml; [yaml.safe_load(p.read_text()) for p in pathlib.Path(".github/workflows").glob("*.yml")]'
bash -n tests/penetration/nikto-scan.sh
python scripts/ci/check_pip_audit_workflow.py
python scripts/ci/supply_chain_gate.py audit
```

Heavy scanner commands remain CI-owned until the digest-pinned tools image is available. `pnpm audit` output is valid only when JSON has the expected advisory/report keys and no `error`; an HTTP/registry error is a scanner failure.

## Failure classification and troubleshooting

1. **Installation/runtime:** command/image cannot start or database cannot initialize. Record the exact command and exit; do not create a findings report.
2. **Scope:** expected path, lockfile, image, endpoint, or rendered IaC is absent/empty. Fail before scanning.
3. **Findings:** scanner completed and emitted a schema-valid report. Preserve it, then apply policy.
4. **Report conversion:** native report exists but JSON/SARIF validation fails. Classify as report failure, not zero findings.
5. **Upload:** validated local evidence exists but GitHub upload fails. Preserve the first scanner status and separately fail evidence publication.
6. **DAST startup:** compose/build, migration, health/readiness, scanner initialization, scan, conversion, and upload are separate states.

## DAST safety and execution

Only scan the workflow-created ephemeral, non-production stack. The default full-scan target is `http://localhost:8004`. Do not dispatch full active DAST against public, production, or third-party targets. Authentication and tenant-scoped DAST remain uncertified until a fake-data tenant fixture and approved auth context are available.

ZAP exit `0` is clean, `1` is warning state, `2` is a policy finding, and other exits are runtime failure. Reports must contain a nonempty `site` list and alert arrays before conversion. Nikto now fails if Docker is missing, the scan process is nonzero, or the report is empty; it never manufactures a zero-finding summary.

`.zap/rules.tsv` remains a governance risk: every ignored rule requires endpoint evidence, owner, expiry, and revalidation before final certification.

## SBOM, SARIF, and artifact policy

The reusable supply-chain workflow is the only release SBOM implementation. It produces deterministic per-component CycloneDX/SPDX filenames and Grype SARIF; release image signing and verification use the digest-pinned CI tools image. The summary reads actual `needs` results and fails before publishing success if required controls failed or were unexpectedly skipped.

Artifacts must include the originating SHA/run metadata, contain no environment credentials, and retain native JSON plus normalized SARIF. A missing artifact or skipped job is never equivalent to zero findings.

## False positives and exceptions

A false positive requires tool/rule, exact location, match reason, unreachable/inapplicable evidence, reviewer/owner, and revalidation condition. A temporary exception additionally requires business justification, compensating control, creation/expiration dates, remediation plan, and revalidation. No new exception or false-positive disposition was created by this stabilization.

## Owner action required to complete certification

Provide an authenticated GitHub-capable runner with Docker/Buildx, registry read access, and the pinned scanner image. Add/fetch `origin/main`, install/authenticate `gh`, rerun all retained scanners on the PR head, inspect native reports and SARIF/artifact uploads, verify live required checks, merge only if all actionable High/Critical findings are resolved, and verify post-merge workflows on the resulting main SHA.
