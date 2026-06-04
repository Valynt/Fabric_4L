# Evidence Bundle for Audit and Release Claims

The evidence bundle is the reviewer-facing archive for release-candidate and audit claims. It consolidates repository-owned readiness evidence into one `tar.gz` file with a checksum manifest so security, compliance, platform, and release reviewers can inspect the same artifact.

## Generate locally

Run the bundle command from the repository root:

```bash
pnpm evidence:bundle
```

The command writes archives to:

```text
artifacts/evidence/evidence-bundle-<commit>-<timestamp>.tar.gz
artifacts/evidence/LATEST
```

List the archive contents with:

```bash
tar -tf artifacts/evidence/*.tar.gz
```

For fresh live release-smoke evidence, run the release-smoke gate first, then regenerate the bundle:

```bash
make test-backend-integrated-release-smoke
pnpm evidence:bundle
```

## Bundle contents

Each archive contains an `evidence-bundle/manifest.json` file. The manifest records:

- generation time, branch, and commit SHA;
- every command run by the generator, including exit code and stdout/stderr artifact paths;
- referenced pre-existing CI/local artifacts copied into the bundle;
- SHA-256 checksum and size for every bundled file.

The bundle includes the following evidence areas:

| Area | Bundle path | Reviewer use |
|---|---|---|
| Maturity scorecard | `maturity/contract-scorecard.json` | Confirms current contract/maturity score and violation counts. |
| Test summaries | `tests/test-summaries.json` and `referenced-artifacts/test-summaries/` | Locates available pytest/JUnit/test-report artifacts. |
| Security scan summaries | `security/security-scan-summaries.json` and `referenced-artifacts/security-scan-summaries/` | Locates available Bandit, Trivy, ZAP, and security regression artifacts. |
| Contract drift reports | `command-output/contract-drift/` and `referenced-artifacts/contract-drift-reports/` | Shows contract compliance command output and copied drift artifacts. |
| OpenAPI breaking-change report | `openapi/breaking-change-report.json` | Records OpenAPI spec inventory, checksums, path counts, and schema counts for baseline comparison. |
| Migration status | `migrations/migration-status.json` and `command-output/migration-status/` | Shows Alembic-managed services and migration entrypoint/head validation output. |
| Container SBOM references | `security/security-scan-summaries.json` and `referenced-artifacts/container-sbom-references/` | Locates CycloneDX/SPDX SBOM files and signed SBOM evidence from CI when present. |
| K8s validation | `command-output/k8s-validation/` and `referenced-artifacts/k8s-validation/` | Shows Kubernetes manifest consistency validation output and copied rendered manifests. |
| Observability validation | `command-output/observability-validation/` | Shows dashboard/rule metadata validation output. |
| CI workflow registry | `ci/workflow-registry.json` and `command-output/ci-workflow-registry/` | Lists workflows and their release, test, security, contract, migration, K8s, and observability categories. |
| Release smoke results | `release/release-smoke-results.json` and `referenced-artifacts/release-smoke-results/` | Locates live L1-L6 release-smoke artifacts when `make test-backend-integrated-release-smoke` has run. |

## CI publication

`.github/workflows/release-evidence-bundle.yml` runs `pnpm evidence:bundle` during consolidation and uploads the generated archive as the `evidence-bundle-<sha>` artifact for pull requests, `main`, `release/**` branches, and version tags. Version-tag runs also attach the bundle to the GitHub Release and request build-provenance attestation for the archive.

## Reviewer checklist

1. Download the `evidence-bundle-<sha>` artifact from the release-candidate workflow run or use the tarball named by `artifacts/evidence/LATEST` from a local reproduction.
2. Verify archive integrity by extracting `evidence-bundle/manifest.json` and checking the `files[*].sha256` values against the archived files.
3. Review `manifest.json.commands` first. Any `finding`, `fail`, `timeout`, or `missing-tool` status is a release-readiness finding unless an owner documents why it is environment-limited.
4. Compare `openapi/breaking-change-report.json` with the previous approved release bundle before accepting OpenAPI breaking-change claims.
5. Confirm live evidence requirements, especially container SBOMs and release smoke results, are present for production release candidates. Local-only bundles may record missing heavyweight artifacts until the corresponding CI jobs or live gates run.
