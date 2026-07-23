# Helm Dependency Preparation for Trivy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate locked Helm dependency preparation from Trivy execution with exact-key caching, bounded fallback, and independently validated evidence.

**Architecture:** A focused Python validator owns the lock/archive/evidence integrity contract. A preparation job restores or builds dependencies and uploads only validated artifacts; the Trivy job consumes and revalidates them.

**Tech Stack:** GitHub Actions YAML, Helm v3.16.2, Python 3.11 standard library, pytest.

## Global Constraints

- Use an exact cache key containing runner OS, architecture, Helm v3.16.2, and `hashFiles('infra/helm/fabric-chart/Chart.lock')`.
- Do not configure `restore-keys`.
- Never use `helm dependency update` or commit Helm `.tgz` archives.
- Cache only `infra/helm/fabric-chart/charts/`, `artifacts/helm-dependencies/checksums.sha256`, and `artifacts/helm-dependencies/metadata.json`.
- Treat cache hits as untrusted and validate before artifact upload.
- Preserve `Chart.lock` and `Chart.yaml` byte-for-byte.

---

### Task 1: Integrity validator and unit coverage

**Files:**
- Create: `scripts/ci/validate_helm_dependencies.py`
- Create: `tests/ci/test_helm_dependency_preparation.py`

**Interfaces:**
- Consumes: `Chart.lock`, chart `.tgz` archives, Helm version.
- Produces: CLI modes `generate` and `validate`; `checksums.sha256` and `metadata.json` evidence.

- [ ] Write pytest fixtures that build small chart archives and a representative lock.
- [ ] Add failing tests for valid generation/validation and for missing, extra, renamed, wrong-version, checksum-mismatched archives.
- [ ] Run `pytest -q tests/ci/test_helm_dependency_preparation.py` and confirm failure because the validator is absent.
- [ ] Implement lock parsing, archive inspection, exact-set comparison, evidence generation, and evidence validation using the Python standard library.
- [ ] Re-run `pytest -q tests/ci/test_helm_dependency_preparation.py` and confirm validator tests pass.

### Task 2: Workflow separation and static contract coverage

**Files:**
- Modify: `.github/workflows/security-gates.yml:188-250`
- Modify: `tests/ci/test_helm_dependency_preparation.py`

**Interfaces:**
- Consumes: validator CLI and validated evidence from Task 1.
- Produces: `prepare-helm-dependencies` artifact required by `trivy-repo-scan`.

- [ ] Add failing static assertions for the exact cache key, pinned cache action, no restore keys, three bounded live attempts, diagnostic artifact, validated artifact, `needs`, download/revalidation, and absence of dependency updates.
- [ ] Run the workflow tests and confirm they fail against the current combined job.
- [ ] Add the preparation job with cache restore, validation, staging-only cleanup, timed retries, evidence generation, post-build validation, immutable-cache save semantics, and always-uploaded diagnostics.
- [ ] Make Trivy depend on preparation, download the artifact, install Helm v3.16.2, revalidate evidence, run `helm dependency list`, verify chart metadata is unchanged, and then scan.
- [ ] Run `pytest -q tests/ci/test_helm_dependency_preparation.py` and confirm all tests pass.

### Task 3: Repository validation and delivery

**Files:**
- Verify all files above.

**Interfaces:**
- Consumes: completed workflow, validator, tests, and design.
- Produces: reviewed commit and pull request.

- [ ] Run `python3 scripts/ci/validate_helm_dependencies.py --help`.
- [ ] Run `pytest -q tests/ci/test_helm_dependency_preparation.py`.
- [ ] Run the repository workflow-reference/static workflow validation applicable to `.github/workflows/security-gates.yml`.
- [ ] Confirm `git diff --check`, no `.tgz` is tracked, and the diff contains no secrets or unrelated changes.
- [ ] Stage only the intended files and commit with a conventional message plus `Co-authored-by: Ona <no-reply@ona.com>`.
- [ ] Create a pull request with summary, validation, governance impact, residual cache-eviction risk, and rollback notes.
