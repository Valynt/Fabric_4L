# V1 Certification Attempt — Candidate e3ace52032f8c80436e46adee4fba27402ae9f31

- **UTC:** 2026-08-11T04:35:00Z
- **Environment:** clean git worktree `/tmp/fabric-cert` @ `e3ace5203` (branch `release-candidate/e3ace5203`), Node v22.17.0 + pnpm 10.18.1 (user-local /tmp), Python 3.12 venv.
- **Rule (Amendment 4):** red-with-named-unblock = PASS for this goal; forced green = automatic FAIL. Nothing below was forced.

## Gate results (exit codes)

| Gate | Command | Exit | Result |
|---|---|---|---|
| Launch contract validation | `make validate-launch-contract` | 0 | PASS (21 tests) |
| Release baseline | `make release-baseline` | 1 | RED — see named causes |
| Candidate certification | `make certify-release-candidate RELEASE_SHA=e3ace5203` (live=False) | 1 | RED at 03a-verify |
| Evidence bundle | `make build-release-evidence RELEASE_SHA=e3ace5203` | 1 | Packet generated, overall FAIL (honest) |

## Named reds and their unblocks

1. **02b-python-setup / baseline setup (first attempt)** — host pip PEP 668 with no project venv in a clean checkout. Unblocked locally by creating `.venv` in the worktree; re-run passed (exit 0, 191.9s). Permanent unblock: certification runs in the hermetic CI/devcontainer environment.
2. **03a-verify / baseline verify** — `typecheck-layer2`: venv numpy 2.5.2 stubs use Python 3.12-only `type` syntax while `services/layer2-extraction/pyproject.toml` sets mypy `python_version = "3.11"`. CI's layer2 mypy (uv-locked dependency set) passes on main; the red comes from installing the monorepo test-requirements set into the certification venv instead of the service's uv-locked env. Named unblock: run certification with per-service uv environments (as CI does) or in the devcontainer. NOT a repo regression observed on main CI.
3. **production-readiness-gate (baseline attempt 1)** — `test_release_candidate_branch_naming` rejects detached HEAD. Named cause: certification worktree was detached; fixed by `git switch -c release-candidate/e3ace5203`. Harness note for the release team: certification docs should state the named-branch requirement up front.
4. **certify 02-install-lockfiles** — initially missing pnpm on host; fixed with user-local Node 22.17.0 + pnpm 10.18.1 (`/tmp/node-v22.17.0-linux-x64`), then PASS (exit 0).
5. **Evidence packet validators FAIL:** `final_testing_launch_gate`, `dependabot_coverage`, `production_readiness_release_authorization`. Launch evidence gates `REQUIRES_ENVIRONMENT`: billing_metering, enterprise_sso_oidc, performance_smoke, production_like_e2e, rollback_restore, telemetry_alerting. Named unblocks: packet (h) staging environment; packet (a) billing decision; packet (g) workflow patches; human release authorization.

## Harness defects found (candidate for a future PR, not fixed here)

- `scripts/release/certify_candidate.py` crashes with `FileNotFoundError`/`ModuleNotFoundError` on missing tools instead of recording a failed step result — certification should fail closed with a recorded reason, not a traceback.
- `docs/launch` (or the certify script) does not surface the named-branch requirement until the release-policy test fails deep in the run.

## What this proves

Repository-owned readiness evidence is composed and classified; live-environment evidence remains outstanding per packet (h). The candidate is **NOT certified** — correctly, fail-closed.

## One-signature acknowledgment

```
Certification attempt reviewed; reds and named unblocks acknowledged.
Name: ______________  Role: Certifier  Date (UTC): __________
```
