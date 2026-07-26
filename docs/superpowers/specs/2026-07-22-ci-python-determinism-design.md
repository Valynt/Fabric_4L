# CI Python Determinism Design

**Status:** Approved design for the first remediation track in the trustworthy-CI program.

**Scope:** Python workflow prerequisites, Layer 2 test authentication, Layer 3 OpenAPI import topology, and Gate Engineering pytest execution.

## Context

Current `main` is not a trustworthy basis for merge readiness because several CI jobs fail before reaching their intended assertions. The relevant failures are independent baseline defects:

- Contract Shape Regression installs only `pytest` and `httpx`, while root pytest startup imports packages such as PyYAML.
- Gate Engineering installs `jsonschema` and PyYAML but invokes a package script that runs `python -m pytest` without installing pytest.
- Layer 2 uses its frozen service lock successfully, then fails during test import because strict runtime startup requires `FABRIC_AUTH_PUBLIC_KEYS` and the job does not declare a test verification key.
- Layer 3 OpenAPI generation imports `layer3_knowledge.api.main`, although the canonical runtime package under `services/layer3-knowledge/src` is `api.main`.
- The existing `.github/actions/setup-fabric-ci` composite centralizes runtime versions but installs the ranged `tests/requirements-test.txt` directly and is adopted by only one proof-of-concept workflow.

These failures are workflow-environment or topology defects. Application behavior, security enforcement, quality thresholds, and test assertions must remain unchanged.

## Goals

1. Make affected Python jobs install complete, reproducible prerequisites before executing tests.
2. Preserve service-local `uv.lock` files as the authority for service jobs.
3. Establish a pinned root-test dependency artifact for root contract and governance jobs.
4. Reuse the existing `setup-fabric-ci` action rather than introducing another setup mechanism.
5. Supply Layer 2 with a valid test-only public verification key without storing a private key or production credential.
6. Make Layer 3 OpenAPI generation import the canonical runtime module.
7. Add static workflow contract tests that prevent these defects from recurring.
8. Emit enough setup metadata to distinguish dependency setup failures from test failures.

## Non-goals

- No application source behavior changes.
- No relaxation of Layer 2 strict-environment authentication.
- No coverage, lint, contract, security, or branch-protection threshold changes.
- No broad migration of every workflow in the repository during this track.
- No fixes for frontend Docker topology, Layer 4 Ruff debt, coverage debt, route audit, Schemathesis, or security scanners; those remain separate tracks.
- No real credentials, private signing keys, or long-lived test secrets in Git.

## Selected Approach

Extend the existing `.github/actions/setup-fabric-ci` composite with explicit dependency modes and migrate only the affected root jobs. Service jobs continue to use their local `uv.lock` directly.

This is preferred over workflow-local patches because it prevents the same incomplete setup from recurring. It is preferred over immediate reusable-workflow consolidation because the latter would combine unrelated job behavior and make the P0 correction difficult to review.

## Dependency Architecture

### Root test lock

Add a generated, checked-in lock file at `tests/requirements-test.lock`.

- Input: `tests/requirements-test.txt`.
- Resolver: the repository-pinned uv version, `0.11.6`.
- Target interpreter: Python 3.11.
- Contents: fully pinned transitive requirements with hashes.
- Update policy: regenerate only when `tests/requirements-test.txt` intentionally changes, then review the dependency diff.
- Integrity gate: a test regenerates the lock in check mode or compares normalized compiled output so input/lock drift fails CI.

The ranged requirements file remains the human-maintained dependency declaration. The lock is the CI installation authority.

### Composite action modes

Enhance `.github/actions/setup-fabric-ci/action.yml` with an explicit `python-dependency-mode` input:

- `root-test`: install `tests/requirements-test.lock` with hash verification.
- `none`: configure Python but do not install Python dependencies.

The composite remains responsible for Python 3.11, Node 22.18.0, and pnpm 10.18.1 setup. It must print actual executable versions and dependency mode to `$GITHUB_STEP_SUMMARY`, not only requested versions.

Service-local setup is intentionally not hidden inside the root-oriented composite in this first track. Layer jobs keep the visible sequence:

```text
uv sync --frozen --all-extras
uv pip install -r ../../tests/requirements-test.lock --require-hashes
```

This preserves the service lock as the primary environment while adding the common root pytest plugins and collection dependencies. The additive installation must not update a service lock.

### Affected root jobs

Contract Shape Regression and Gate Engineering use `setup-fabric-ci` in `root-test` mode. Their hand-written `pip install` steps are removed. Existing Node installation remains enabled only where the job executes pnpm scripts.

## Layer 2 Authentication Contract

Layer 2 remains a strict runtime during CI. Store one test-only public key set at `config/ci/fabric_auth_test_public_keys.json` in the documented JSON list shape. The file contains the complete PEM-encoded public key under `public_pem` and the fixed key ID `ci-test-only`; it contains no private key.

Before Layer 2 validation, a named workflow step loads the compact JSON into the job environment:

```bash
printf 'FABRIC_AUTH_PUBLIC_KEYS=%s\n' "$(jq -c . config/ci/fabric_auth_test_public_keys.json)" >> "$GITHUB_ENV"
```

Only public material is stored. No matching private key is required for Layer 2 collection and ordinary unit tests. If a test needs signed Fabric-auth envelopes, it must generate an ephemeral key pair inside the test or job and must not reuse this public-only fixture as a credential.

The job also declares the documented issuer, audience, and `FABRIC_AUTH_MODE=observe` when those values are required by application initialization. Tests that assert strict fail-closed startup continue to override or delete variables with `monkeypatch`; the workflow environment does not weaken those tests.

The public key is never duplicated as multiline YAML. The workflow contract test validates that the job references `config/ci/fabric_auth_test_public_keys.json` and that neither the fixture nor the workflow contains a private-key PEM block.

## Layer 3 OpenAPI Topology

The generation matrix must express both module and working directory explicitly:

- Layer 3 working directory: `services/layer3-knowledge`
- Layer 3 module: `api.main`
- Layer 3 source path: `src`
- Layer 5 retains its existing package module and working directory.

The generation command imports from the matrix-provided working directory with its `src` directory on `PYTHONPATH`, matching the checked-in Layer 3 runtime topology and pytest configuration. It must not reintroduce the removed `layer3_knowledge` compatibility namespace.

## Failure Semantics and Diagnostics

Setup and validation remain separate named steps so the first independently failing command is visible.

Each migrated job records:

- Python executable and actual version;
- uv and pip versions when applicable;
- selected dependency mode and lock-file path;
- a dependency integrity result;
- the exact validation command that follows setup.

A setup failure must stop the job before tests run. A test failure must not be labeled as dependency installation failure. Aggregate gates are outside this track and continue to consume the job result unchanged.

## Validation Strategy

### Static workflow contracts

Add focused tests under `tests/ci/` that parse the workflow YAML and composite action. They assert:

1. Contract Shape Regression uses `root-test` mode and contains no ad hoc package list.
2. Gate Engineering uses `root-test` mode and therefore has pytest available.
3. Layer 2 uses `uv sync --frozen --all-extras`, installs the pinned root-test lock additively, and declares the canonical public-key fixture.
4. Layer 3 OpenAPI generation uses `api.main` from `services/layer3-knowledge` and rejects `layer3_knowledge.api.main`.
5. The composite installs the pinned lock with hash enforcement in `root-test` mode.
6. The root test lock is synchronized with `tests/requirements-test.txt`.
7. No checked-in CI fixture contains a private-key PEM block.

### Local execution

Run the narrowest affected commands in clean Python 3.11 environments:

- Contract Shape Regression collection and execution.
- Gate Engineering validation and pytest suite.
- Layer 2 full collection, followed by its smallest auth-enforcement subset.
- Layer 3 OpenAPI import and schema generation.
- Workflow contract tests.

Dependency and generated-contract diffs must be inspected after every command. No service `uv.lock`, package manifest, OpenAPI contract, or application source file may change unexpectedly.

### CI rollout

Push the isolated branch and observe the four root jobs first. Re-run their aggregate consumers only after the root jobs pass. Record links to both the pre-fix failure and post-fix successful run in the pull request validation section.

## Security Properties

- Root dependencies are hash-verified and pinned.
- Service locks remain frozen.
- The Layer 2 fixture contains public material only.
- Authentication strictness is unchanged.
- No lifecycle, integrity, or security checks are bypassed.
- No quality threshold is reduced.

## Rollback

The change is workflow-only plus dependency lock and tests. Rollback consists of reverting the composite adoption and workflow edits together. The root test lock may remain harmlessly checked in, but the preferred rollback reverts it and its drift test as one unit to avoid an orphaned authority.

## Follow-on Tracks

After this track is validated independently:

1. Frontend Docker workspace topology and pnpm provisioning.
2. CI root/cascade classification and merge-readiness evidence reporting.
3. Jest/Babel/Istanbul and Schemathesis compatibility.
4. Layer 4 Ruff, frontend and Layer 5 coverage, OpenAPI documentation, and route governance.
5. Scanner-specific security remediation and owned waivers.
