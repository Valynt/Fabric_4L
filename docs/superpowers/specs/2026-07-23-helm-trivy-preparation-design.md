# Helm Dependency Preparation for Trivy Design

## Goal

Make Helm chart rendering preparation an independently reported security-gate job, while avoiding mutable public repository indexes on normal scans through an exact lock-digest-keyed GitHub Actions cache.

## Architecture

`prepare-helm-dependencies` checks out the repository, installs Helm v3.16.2, and restores only the chart dependency directory plus integrity evidence from an exact cache key containing runner OS, runner architecture, Helm version, and the SHA-256 of `Chart.lock`. The cache has no prefix restore keys. A cache hit is always revalidated; it is never treated as integrity proof.

On a cache miss or invalid cache hit, the job clears only dependency staging and evidence, then performs up to three bounded attempts to register/update the two public repositories and run `helm dependency build`. Each command is timed out and logged. It generates per-archive checksums and metadata only after the locked dependencies validate, then uploads the validated dependencies and diagnostics as workflow artifacts.

`trivy-repo-scan` depends on preparation, checks out the same commit, installs the same Helm version, downloads the prepared artifact, revalidates checksums and metadata, confirms Helm reports the dependencies as ready without changing `Chart.yaml` or `Chart.lock`, and only then invokes Trivy. Helm availability failures therefore belong to preparation; vulnerability or scanner failures belong to Trivy.

## Integrity Contract

The validator derives the expected dependency names, repositories, and versions from `infra/helm/fabric-chart/Chart.lock`. It requires exactly one `.tgz` for each locked dependency and no extra archives. Archive filenames and embedded `Chart.yaml` names/versions must match the lock. Evidence records the exact lock SHA-256, Helm version, dependency metadata, archive paths, and archive SHA-256 values. Validation checks every field and checksum.

Both jobs run `helm dependency list` and `git diff --exit-code -- Chart.lock Chart.yaml`. Live preparation uses `helm dependency build`, never `helm dependency update`. No chart archive is committed.

## Failure Handling

Invalid restored content is deleted only from `infra/helm/fabric-chart/charts/` and `artifacts/helm-dependencies/`, rebuilt once through the bounded live-resolution routine, and revalidated. An invalid cache entry is not mutated; GitHub Actions only saves when the exact key was absent. Diagnostics are uploaded with `if: always()`, including cache state, commands, attempts, repository failures, and validation output.

## Validation

Unit tests exercise valid evidence and missing, extra, renamed, wrong-version, and checksum-mismatched archives. Static workflow tests assert the exact cache identity, absence of restore keys and dependency updates, bounded fallback, validated-only artifact upload, the preparation dependency, and consumer-side artifact validation.

## Residual Risk and Rollback

GitHub Actions may evict caches. A miss still depends on public Helm repositories, but bounded retries and separate diagnostics prevent an outage from being mislabeled as a Trivy failure. Rollback is limited to reverting the workflow, validator, and tests; no runtime, API, tenant, contract, or migration state changes.
