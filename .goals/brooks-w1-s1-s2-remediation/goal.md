# Goal: Remediate Brooks review W1/S1/S2 in Layer 4 tests

## User Request

"Remediate and address each of the three items from the brooks review. Make the smallest cohesive correction, avoid broad unrelated cleanup, validate progressively, and inspect the final patch for weakened tests, baselines, thresholds, generated artifacts, or CI behavior."

The review (Brooks audit of the Value Fabric monorepo) scored Layer 4 test hygiene **92/100** and raised four findings. Three are code-addressable with a small cohesive change and are in scope here:

- **W1** — environment-gated (postgres/Docker) tests skip silently, masking coverage.
- **S1** — wall-clock sleeps in tests invite CI flakes.
- **S2** — the per-service pytest marker registry drifted (the exact bug this branch already fixed: layer4's registry was truncated; this session's earlier commit `d9bcf3f6b` re-registered all 15 used markers). The fourth finding (S3 — generic method-style test names like `test_to_dict`) is an explicit **out-of-scope** mass rename.

## Refined Goal

Address the three findings above in `services/layer4-agents` with the smallest cohesive correction each. No production (non-test) source changes, no new dependencies, no new CI infrastructure.

- **W1** — in `tests/conftest.py`, make the Docker/testcontainers-gated skip path: (a) emit a config-time warning naming the skip count and why when environment skips are applied (no longer silent), and (b) fail **closed** at collection when an operator explicitly requires those tests via a new opt-in env var `LAYER4_REQUIRE_TESTCONTAINERS` but the environment cannot actually run them. The existing `skip_postgres = pytest.mark.skip(...)` / `skip_docker = pytest.mark.skip(...)` assignment lines and the four `pytest.skip(...)` reason strings must remain byte-identical so the content-matched skip-debt register stays green.
- **S1** — eliminate or determinize fixed sleeps in the layer4 test suite: OIDC expiry tests get a controllable virtual clock (patch `datetime.now(UTC)` in the production store module and `time.time` in the test's `_FakeRedis`); propagation waits become predicate-based via one tiny shared `wait_until` helper; the `SlowTool` timeout experiment gets ~20x faster; any genuine latency-simulation sleep stays ≤0.1s and is documented.
- **S2** — add `--strict-markers` to layer4's `[tool.pytest.ini_options].addopts`, matching the existing `services/layer2-extraction` precedent (`addopts = "-ra -q --strict-markers --tb=short"`), so any future used-but-unregistered marker hard-fails instead of silently warning. This is provably safe today: a full `--collect-only --strict-markers` against the current tree collects **3274 tests with exit 0**.

## Acceptance Criteria

Each criterion requires **fresh evidence run after the Builder's commit** (not reused from this goal's planning probes).

### W1 — visibility + fail-closed env-gated skips
- [ ] **A1** — With `LAYER4_REQUIRE_TESTCONTAINERS=1` set in this environment (no Docker daemon / testcontainers), `pytest --collect-only` on `services/layer4-agents/tests` exits non-zero with a `pytest.UsageError` whose message cites the skip-register IDs (`VF-SKIP-119` / `VF-SKIP-120`). With the var unset, the same command succeeds and environment-gated tests skip exactly as they do today (same messages, same counts, no behavior change).
- [ ] **A2** — When the environment-skip branch applies in `pytest_collection_modifyitems`, a config-time warning is emitted naming the skip count, the category (missing `testcontainers` and/or no Docker daemon), and the escape-hatch env var. Visible in a normal `pytest -q` run (Inspector verifies by capturing warning output).
- [ ] **A3** — The registered conftest skip lines/reasons are byte-identical (skip_postgres assignment, skip_docker assignment open line, the four `pytest.skip(...)` reason strings). `make check-pytest-skip-governance` body reports **no TDG201 (unregistered)** and **no TDG203 (stale)**. The diff does not touch `config/ci/test_skip_register.yaml`, root `pytest.ini`, `Makefile`, or `.github/workflows/*`.

### S1 — deterministic tests
- [ ] **A4** — `tests/test_oidc_state_store.py::test_in_memory_store_enforces_expiry` and `::test_redis_store_enforces_expiry` contain **no** `time.sleep`/`asyncio.sleep`. Expiry is proven with a virtual clock — patch the production module's `datetime.now(UTC)` (module `layer4_agents.shared.identity.oidc_state`) and the test-local `_FakeRedis`'s `time.time` — so the valid-consumption path and the post-advance expired path are both asserted deterministically with zero wall-clock dependence.
- [ ] **A5** — `tests/test_agent_tool_result_contracts.py::SlowTool.execute` sleeps ≤0.05s (still greater than its `timeout_seconds = 0.01`), with a comment stating the sleep exists only to exceed the tool timeout. The timeout contract tests still pass and still exercise the timeout path.
- [ ] **A6** — New tiny module `tests/_wait_utils.py`: `async def wait_until(predicate, *, timeout=2.0, interval=0.01, description="condition")` raising `AssertionError` (with `description`) on timeout. The fixed propagation sleeps at these sites are converted to predicate-based waits on observable state (mock `call_count`, ready flags, emitted events, awaited coroutines):
  - `tests/test_oidc_cleanup.py` ~lines 113, 138, 170
  - `tests/test_messaging.py` ~lines 215, 232, 255, 275, 295, 334, 471
  - `tests/test_resilience.py` ~lines 305, 335, 365
  - `tests/test_health_tracker.py` ~line 261
  - `tests/test_tool_result_contract.py` ~lines 512, 537
  No fixed sleeps remain at those sites. Leave **untouched**: `tests/test_redis_message_bus_contract.py` ~`:153` keep-alive `create_task(asyncio.sleep(60))` and the already-deterministic `tests/test_oidc.py` `asyncio.sleep` patch pattern.
- [ ] **A7** — No new wall-clock sleeps anywhere in the diff. Any remaining latency-simulation sleep (e.g. `tests/unit/test_audit_orchestrator_analyzers.py::_SlowReadStream`) is ≤0.1s and carries a comment stating it simulates latency. Unit-suite gates pass with pass counts equal to the pre-change baseline (within ±1; the 8–12 Docker-gated skips in this Docker-less environment are unchanged in kind) and wall time **no greater** than the pre-change baseline (expected strictly less — OIDC + SlowTool changes alone remove ~2.3s).

### S2 — marker-registry drift locked
- [ ] **A8** — `services/layer4-agents/pyproject.toml` `[tool.pytest.ini_options].addopts` becomes `-v --tb=short --strict-markers`. Full `--collect-only --strict-markers` still collects 3274 tests with exit 0 (no unknown/unregistered marker failures); the unit-suite gates pass. No other service's pytest config and no root `pytest.ini` change.

### Cross-cutting
- [ ] **A9** — Resolve the interpreter with `& python scripts/ci/resolve_python.py` and run all gates with it. The mypy baseline gate (`check_mypy_baseline.py --service-dir services/layer4-agents --baseline config/ci/mypy_baseline_layer4.json --paths src`) reports 0 errors. No test assertion is weakened, no baseline/threshold relaxed, no generated artifact modified, and no CI behavior weakened anywhere in the diff.

## Scope Boundaries

**In scope:**
- `services/layer4-agents/tests/conftest.py` — W1 guard + warning only; the registered skip/`pytest.skip` reason lines stay verbatim.
- `services/layer4-agents/pyproject.toml` — `addopts` gains `--strict-markers`.
- The S1 test files named in A6 (+ `test_oidc_state_store.py`, `test_agent_tool_result_contracts.py`), plus the new `tests/_wait_utils.py`.
- Inline documentation of `LAYER4_REQUIRE_TESTCONTAINERS` (conftest docstring/comment, not `.env.example`).

**Out of scope:**
- S3 (renaming generic test names) — explicitly excluded as broad cleanup.
- `config/ci/test_skip_register.yaml`, root `pytest.ini`, `Makefile`, `.github/workflows/*`, `.env.example`.
- Any other service's pytest/marker/`--strict-markers` configuration (L1/L2/L3/L5/L6).
- Production (non-test) source changes; new dependencies; new CI jobs; new lint/baseline tooling.
- Refactoring that goes beyond the three findings.

## Applicable Project Conventions

**Quality gate commands** (Windows PowerShell — `;` chaining only, no `&&`/`||`):

Resolve the interpreter first, then reuse `$py`:
```powershell
$py = (& python scripts/ci/resolve_python.py).Trim()
```

Baseline FIRST (before any edit), then re-run the identical commands after the change and compare:
```powershell
# Local unit profile (mirror of `make test-layer4`, Windows-safe: tmp_path lands in %LOCALAPPDATA%\Temp,
# outside the repo, preserving the "assert no git repo" test premise)
& $py -m pytest services/layer4-agents/tests -o cache_dir=..\..\.tmp\pytest-cache-layer4 `
  -m "not postgres and not requires_postgres and not docker and not integration and not e2e" -p no:randomly -q

# Full collection under strict markers (proves every used marker is registered)
& $py -m pytest services/layer4-agents/tests --collect-only -q --strict-markers -p no:randomly

# W1 fail-closed probe (this env has no Docker): expect non-zero + UsageError citing VF-SKIP-119/120
$env:LAYER4_REQUIRE_TESTCONTAINERS="1"; & $py -m pytest services/layer4-agents/tests --collect-only -q -p no:randomly; Remove-Item Env:LAYER4_REQUIRE_TESTCONTAINERS

# Skip governance (make check-pytest-skip-governance body): expect 0 violations, no TDG201/TDG203
& $py -m pytest --collect-only -q -ra tests > artifacts/pytest-collection.txt
& $py scripts/ci/check_pytest_skip_governance.py artifacts/pytest-collection.txt --write-report artifacts/test-debt-governance.json

# mypy baseline ratchet (make typecheck-layer4 body): expect 0 errors
& $py scripts/ci/check_mypy_baseline.py --service-dir services/layer4-agents --baseline config/ci/mypy_baseline_layer4.json --paths src
```

Pytest config inheritance: root `pytest.ini` sets `--strict-markers --timeout=60 --import-mode=importlib`; when running under `services/layer4-agents`, that service's `pyproject.toml` `[tool.pytest.ini_options]` is the configfile and its `addopts` **replaces** the root `addopts`. Windows path note: the Makefile's `TMPDIR=/tmp` is POSIX-only — do not run literal `make test-layer4` on Windows; use the direct pytest invocation above.

**Commit convention:**
- Conventional commits with a role bracket in the title (≤72 chars):
  - Builder: `type(scope): [B] description`
  - Inspector: `chore(scope): [I] description`
- Trailer required: Builder `Assisted-by: OpenAI:GPT-5.6 Luna`; Inspector `Assisted-by: OpenAI:GPT-5.6 Sol`.
- Exactly one commit per agent per iteration; the Builder commits all implementation in a single commit.

**Guidelines / rules:**
- Repo governance: `docs/governance/behavior-first-testing.md`, `docs/governance/compatibility-debt-registry.md` — the skip-debt register is content-matched and must not go stale (A3).
- Environment reality: this Windows sandbox has **no Docker daemon** and no guaranteed `testcontainers`; that is precisely the W1 "environment cannot run gated tests" scenario for A1/A2.
- Working tree is clean at start; HEAD is `895cfd9637a5dcc14eb71ffa6566ea082776f357`. Do not run destructive git commands.