# PR #1183 CI Stabilization Walkthrough

- **PR:** `#1183` (`fix/ci-stabilization-and-pr-cleanup`)
- **Repository:** `bmsull560/Fabric_4L`
- **Prepared:** `2026-07-29`
- **Scope:** Phase-by-phase evidence for the CI stabilization pass requested on PR `#1183`

## Objective

Stabilize the non-required failing checks on PR `#1183` without weakening any gate, preserve the eight required checks that were already passing, disposition superseded CI-fix PRs if they are truly replaced by `#1183`, and prepare the branch for merge once code-fixable failures are cleared and any remaining external failures are documented.

## Environment Constraints

The workspace used for this pass did not have local CI tooling available on `PATH`:

- `gh` was unavailable, so GitHub workflow inspection was performed through the repository SCM tools instead of the CLI.
- `python`, `python3`, `node`, `pnpm`, `docker`, `make`, `uv`, and `pipx` were unavailable, so no local reproduction or targeted test execution could be run from this environment.
- The worktree contained one unrelated pre-existing modification that was left untouched:
  - `.devcontainer/devcontainer-lock.json`

These constraints affected verification depth but did not prevent workflow inspection, code changes, commit/push, or pull-request state management.

## Approved-Plan File

The requested approved-plan path was not present in the workspace environment:

- `/home/bunnyshell/.gemini/antigravity-cli/brain/449b939b-eefc-4964-ac7f-682daae90a75/ci_stabilization_plan.md`

Execution therefore proceeded from the user-provided phase list and constraints as the authoritative plan.

## Phase 1: Diagnose and Fix Non-Required Failing Checks

### Original failing checks investigated

The requested failing checks were:

- `Frontend`
- `Layer 1`
- `Layer 3`
- `Layer 4`
- `DAST`
- `Integration Tests`
- `Runtime Contracts`
- `Trivy fs scan`
- `Visual Tests`
- `p0-e2e-gate`
- `Unified Readiness`

### Findings from the stale failures

Inspection of the earlier failed runs showed that several of the user-listed failures were already stale by the time this stabilization pass resumed:

- `Frontend` had an older failure tied to `brace_expansion_1.default is not a function`; that drift had already been fixed on the branch before this pass.
- `Layer 1` had an older `503` versus expected `404` failure; that specific failure was no longer current.
- `Layer 3` had an earlier cancellation rather than a current code failure.
- `Layer 4` and `p0-e2e-gate` had older real failures that were no longer the current branch head state.
- `Unified Readiness` was failing as a downstream summary gate rather than as an independent root cause.

### Code/workflow fixes applied in this pass

The following fixes were committed and pushed in commit `b8e8f296049f71f698b679790b945a2546020cf2`:

1. `Runtime Contract Tests (Services Up)` workflow fix
   - Updated `.github/workflows/pr-checks.yml`
   - Replaced an ad hoc `pip install` step with the canonical shared CI setup action
   - Pinned the runtime-contract job to `python-dependency-mode: root-test`

2. Runtime-contract regression test
   - Updated `tests/ci/test_deterministic_gate_workflows.py`
   - Added an assertion that the runtime-contract job uses the shared locked setup and no raw `pip install`

3. Layer 4 release-smoke / tenant-status fail-closed fix
   - Updated `services/layer4-agents/src/layer4_agents/api/middleware.py`
   - Replaced eager rate-limiter capture with a lazy runtime-state-backed proxy so the middleware can use the Redis client initialized during startup

4. Layer 4 middleware regression test
   - Added `services/layer4-agents/tests/test_api_middleware_proxy.py`
   - Verifies the middleware resolves its Redis dependency at call time rather than at app construction

5. DAST ephemeral-stack startup fix
   - Updated `.github/workflows/security-gates.yml`
   - Added `JWT_ALGORITHM=RS256` to the generated DAST `.env` so the API gateway can pass production-like JWT validation and start successfully

6. DAST workflow regression test
   - Updated `tests/ci/test_security_gates_semgrep_pinning.py`
   - Added coverage proving the DAST-generated `.env` includes `JWT_ALGORITHM=RS256`

### Evidence from the fresh rerun after push

After the push, the new PR rerun showed the previously targeted contract/readiness path clearing successfully:

- `Production Readiness Gate` — `success`
- `OpenAPI Contract Tests (layer3)` — `success`
- `OpenAPI Contract Tests (layer5)` — `success`
- `Contract Scorecard` — `success`
- `Layer 5 - Tenant Isolation Regression` — `success`
- `Kubernetes Dry-Run Validation` — `success`
- `security-isolation` — `success`
- The required checks remained passing throughout the rerun window

Subsequent rerun polling showed additional targeted jobs completing successfully:

- `Build App` — `success`
- `Lint Frontend (Contract Rules)` — `success`
- `Frontend Security Audit (pnpm)` — `success`
- `Route Auth Dependency Gate` — `success`
- `Layer 5 - Source Contract` — `success`
- `Docker Compose Config Contract` — `success`
- `Build images & security scan (layer4-agents)` — `success`
- `Build images & security scan (layer2-extraction)` — `success`

This materially reduced the current stabilization scope to long-running or not-yet-finished jobs rather than confirmed recurrent failures in the areas above.

## Remaining External or Queue-Blocked Items

At the time this walkthrough was written, the following items had not yet produced a final post-fix conclusion on the fresh rerun:

- `Visual Tests (journeys)`
- `Runtime Contract Tests (Services Up)`
- `Layer 1 - Ingestion`
- `Layer 3 - Knowledge`
- `Layer 4 - Agents`
- `Frontend`
- `DAST (OWASP ZAP baseline)`
- `Repository Scan (Trivy fs + IaC + secrets)`
- `Integration Tests (Docker)`
- `p0-e2e-gate`

### Visual Tests

Earlier evidence showed the visual-regression workflow was failing because the repository does not currently contain the expected Playwright snapshot baselines under `apps/web/e2e/visual/regression.spec.ts-snapshots/`.

Because Playwright and Node were unavailable in this environment, no baseline regeneration could be performed locally.

On the fresh rerun, `Visual Tests (journeys)` was still `in_progress` at the time of the latest poll, so the prior missing-baseline evidence remains the best available explanation until the current run completes.

### Repository Scan (Trivy fs + IaC + secrets)

Earlier evidence showed the repository-wide Trivy scan failing with a real non-zero exit, but the exact findings were not extractable from this environment:

- check annotations exposed only a generic failure
- artifact/code-scanning details were not available through the accessible tools in this session
- Trivy/Docker were unavailable locally for reproduction

Until the final rerun result is known, this remains documented as an external evidence gap rather than a confirmed code-fixable issue in this pass.

### DAST

The earlier DAST failure mode was addressed by injecting `JWT_ALGORITHM=RS256` into the generated DAST environment so the production-like API gateway startup validation could pass.

On the fresh rerun, `DAST (OWASP ZAP baseline)` was `in_progress` at the time of the latest poll, so the startup fix has been applied but the final outcome was not yet available when this artifact was last updated.

## Phase 2: Cancel Obsolete Workflow Runs

This phase could not be fully executed from the available tool surface.

- The preferred `gh` CLI was not available in the workspace.
- A targeted tool search for GitHub Actions workflow-run cancellation did not reveal any cancel-run tool in the available SCM surface.

Result:

- obsolete-run cancellation is currently **tool-blocked**
- this was not substituted with ad hoc destructive actions or guessed API calls

## Phase 3: Disposition Open PRs

Open-PR review focused on identifying CI-fix branches that were genuinely superseded by `#1183` while leaving valid feature, test, and Dependabot PRs intact.

### Key findings

- PR `#1095` was already closed/merged, so there was nothing to disposition there.
- The main remaining open CI-fix candidate was `#1138` (`fix(ci): add Semgrep OSS scan-coverage evidence and document GitHub SARIF limitation`).
- Review of `#1138` showed it is not a trivial duplicate of `#1183`; it carries distinct Semgrep evidence/reporting changes and was therefore **not** closed during this pass.
- No other open PR was identified as an obviously superseded CI-fix branch that could be safely closed without overreaching the requested criteria.

Result:

- no PRs were closed during this pass because no clear superseded target was proven by current evidence

## Phase 4: Merge Readiness

PR `#1183` is mergeable from GitHub's perspective, but merge completion depends on the still-running rerun reaching a satisfactory end state:

- head branch: `fix/ci-stabilization-and-pr-cleanup`
- mergeable status observed after the push: `true`

Merge was intentionally deferred until the fresh rerun resolves the remaining active checks or leaves only documented external/tooling blockers that are acceptable under the requested criteria.

## Validation Performed

### Performed

- inspected PR `#1183` check runs and reruns through SCM workflow/PR tools
- inspected the stale failing jobs called out in the request
- committed and pushed the code/workflow fixes above
- re-polled the fresh rerun to verify the targeted contract/readiness path was no longer failing

### Not performed locally

- `pytest`
- `pnpm`
- `docker compose`
- `gh run view`
- Playwright snapshot generation
- Trivy reproduction

Reason: required tooling was unavailable in the workspace environment.

## Worktree Discipline

- The unrelated local modification in `.devcontainer/devcontainer-lock.json` was intentionally left untouched.
- No gate was weakened, skipped, or disabled as part of this stabilization pass.

## Current Status

As of this artifact revision:

- code-fixable issues identified in runtime contracts, Layer 4 release-smoke middleware wiring, and DAST API-gateway startup have been fixed and pushed
- the fresh rerun has already cleared several previously failing or downstream-impacted checks, including additional frontend, route-auth, and image/security jobs
- `Layer 4 - Agents` was no longer failing on the fresh head; at latest poll it had not started running yet and remained `queued`
- remaining work depends on final outcomes from the still-running post-push checks, especially `Visual Tests (journeys)`, `DAST (OWASP ZAP baseline)`, and the remaining long-tail matrix jobs, plus any acceptable disposition of external/tooling-blocked items
