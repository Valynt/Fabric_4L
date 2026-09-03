# Goal: Remediate brooks-lint T2a / T3 / T4 / T5 test-quality findings in services/layer4-agents

## User Request

The user invoked `/goal` with: "take one more pass addressing the warnings and issues identified", attaching
the Brooks-Lint Test Quality Review of the prior W1/S1/S2 remediation (score 84, `.brooks-lint-history.json`
6th entry). The review reported 0 critical / 3 warning / 1 suggestion:

- **W1 (T2a)** — TokenBucket tests in `test_resilience.py` keep wall-clock `time.time()` and a weak
  `tokens <= 5.0` non-increase assert, while circuit-breaker tests in the same file got a virtual clock;
  a no-decrement regression would still pass.
- **W2 (T4)** — Test coupling to private members (`breaker._update_state()`/`_lock`, `task._task`,
  `router._agent_load`, `tracker._badges`) creates false-failure risk on internal refactors.
- **W3 (T5)** — The fail-closed skip gate (conftest `UsageError` + config-time warning) has no committed
  automated test; it was verified only by manual invocation, so the gate could silently regress.
- **S1 (T3)** — Near-duplicate store/consume setup in the OIDC factory test.

Standing user directives this goal honors: make the **smallest cohesive correction**, avoid broad unrelated
cleanup, validate progressively, and **no weakened tests / baselines / thresholds / generated artifacts /
CI behavior edits**.

Phase-0 interview was **skipped** (autopilot mode: "Decide; don't ask"; the ARGUMENTS name the exact
findings). The prior goal `.goals/brooks-w1-s1-s2-remediation/goal.md` provides the repo conventions and
validation history.

## Refined Goal

Make the layer4 test suite deterministic and resilient to production refactors by (1) replacing the three
remaining wall-clock TokenBucket tests with the virtual-clock pattern already used by the circuit-breaker
tests and **strengthening** the weak no-decrement assert to an exact-expectation one; (2) removing test
coupling to private members via tiny additive, behavior-preserving public seams (or documented handshakes
where no small seam exists); (3) adding a committed, environment-deterministic regression test for the W1
fail-closed skip gate (the env-var parsing, the `UsageError` fail-closed path, and the config-time warning
path); and (4) de-duplicating the OIDC store/consume round-trip tests via a shared helper. No production
behavior, test count, marker set, CI, or baseline files change.

## Acceptance Criteria

**AC-1 (W1 / T2a) — TokenBucket tests fully deterministic + strengthened assert.**
- In `services/layer4-agents/tests/test_resilience.py`:
  - `test_consume_succeeds_when_tokens_available` uses the same frozen virtual clock as the circuit-breaker
    tests (`clock = {"now": 1_000.0}`; `monkeypatch.setattr(time, "time", lambda: clock["now"])`), so no
    refill can occur between construction and `consume(1)`, and asserts the **exact** decrement
    (`assert bucket.tokens == pytest.approx(4.0)` from `tokens=5.0`), replacing the weak
    `assert bucket.tokens <= 5.0` and its tolerance comment.
  - `test_refill_adds_tokens_over_time` and `test_refill_does_not_exceed_capacity` set `last_refill` to a
    fixed virtual pivot (e.g. `clock["now"]` at a constant like `1_000.0`) and advance `clock["now"]` by the
    simulated elapsed interval; they must not call real `time.time()`. The `approx(10.0)` / `approx(5.0)`
    expectations are unchanged.
  - No new wall-clock `sleep`/`time.time()` dependence is introduced anywhere in the file; the virtual-clock
    pattern and `_wait_utils.wait_until` polling are the only timing mechanisms.

**AC-2 (W2 / T4) — No test reads or writes `_`-private members of production objects.**
For each site below, the listed test file must no longer access the named private attribute. Preferred seam
(first listed); the documented-handshake alternative is acceptable only where noted.
1. `tests/test_oidc_cleanup.py` `test_cleanup_task_start_stop` (`task._task`): add a read-only
   `running` property to `OIDCCleanupTask` (`return self._task is not None`) and assert
   `task.running is True` / `task.running is False`.
2. `tests/test_messaging.py` `test_update_agent_load_clamps` (`router._agent_load["agent-1"]`): add a
   public `get_agent_load(agent_id: str) -> int` accessor on `MessageRouter`
   (`return self._agent_load.get(agent_id, 0)`) and assert `router.get_agent_load("agent-1") == 100`
   and `== 0` after the clamps.
3. `tests/test_resilience.py` circuit-breaker tests (`breaker._lock` + `breaker._update_state()` at the
   ~three sites that deterministically advance OPEN→HALF_OPEN): add a minimal public
   `async def refresh_state(self) -> None` on `CircuitBreaker` (`async with self._lock: await
   self._update_state()`) with a docstring, and replace each
   `async with breaker._lock: await breaker._update_state()` with `await breaker.refresh_state()`.
   The virtual-clocked HALF_OPEN assertions themselves are unchanged.
4. `tests/test_health_tracker.py` `test_auto_hide_badge` (`tracker._badges`, `tracker._auto_hide_badge`,
   `tracker._auto_hide_tasks`): **documented handshake is the default fix** — no public API can create a
   short-delay auto-hide badge (the two `AUTO_HIDE_AFTER_SECONDS` configs used by real components are 60s),
   so add an explicit comment explaining why the test drives `_auto_hide_badge` directly (deterministic,
   avoids a 60s real wait) and that the wait/assertion reads the public `get_active_badges()`. The waits
   must keep using `_wait_utils.wait_until` over `get_active_badges()`. A tiny public seam is also
   acceptable if ≤ a few lines and behavior-preserving, but is not required.
- Every added production member has a docstring/comment, is additive only, and changes no existing public
  signature or behavior.
- Scan gate: no remaining `._lock`, `._update_state`, `_agent_load[`, `._task`, `._badges[`,
  `._auto_hide_` private-member reads/writes in the four test files, except the explicitly documented
  health-tracker handshake.

**AC-3 (W3 / T5 — highest value) — committed regression test for the fail-closed skip gate.**
Create `services/layer4-agents/tests/test_skip_gate.py` covering the real `tests/conftest.py` functions,
**environment-deterministically** (no subprocess; monkeypatch module-level flags; must be green whether or
not Docker exists in this sandbox):
1. `conftest._testcontainers_required()`: `LAYER4_REQUIRE_TESTCONTAINERS` in `{"1","true","yes","TRUE"}`
   → `True`; unset / `{"0","no","false"}` → `False`.
2. Fail-closed path: with `conftest.POSTGRES_AVAILABLE = False` and `conftest.DOCKER_AVAILABLE = False`
   monkeypatched, and the env var set, `conftest.pytest_collection_modifyitems(stub_config, stub_items)`
   raises `pytest.UsageError` whose `str` contains `LAYER4_REQUIRE_TESTCONTAINERS` and `VF-SKIP-119` /
   `VF-SKIP-120`.
3. Warning path: both flags `False`, env unset → stub items with `postgres` in `keywords` receive a skip
   marker, and `stub_config.issue_config_time_warning` receives a `RuntimeWarning` whose `str` starts with
   `Skipped N` (N ≥ 1) and mentions the gated items. Note the real conftest logic: when
   `POSTGRES_AVAILABLE` is False the `elif`, not-Docker branch is not reached — `docker`-only items are
   **not** skipped in that configuration; the test must match this exactly (only postgres-keyworded items
   counted).
4. Optional but encouraged: `POSTGRES_AVAILABLE = True`, `DOCKER_AVAILABLE = False`, env unset → items with
   `postgres` **or** `docker` keywords get skipped and the warning is emitted (exercises the `elif` branch).
- Stub item classes only need `keywords` to support `"x" in keywords` and an `add_marker` method; a stub
  config only needs `issue_config_time_warning(warning, stacklevel=...)`. Import the conftest module with
  `import conftest` (pytest has already loaded it); if that import is unreliable under the rootdir
  import-mode, read it from `sys.modules["conftest"]`. Do not modify `conftest.py` itself.
- The new file carries `pytest.mark.unit` and **no** postgres/docker markers, so it runs in the standard
  unit profile and is never gate-skipped.

**AC-4 (S1 / T3) — de-duplicate OIDC store round-trip.**
- `tests/test_oidc_state_store.py`: add a small module-level helper `_assert_one_time_use(store, key,
  verifier)` that stores, asserts `validate_and_consume(key) == verifier`, then asserts a second consume
  returns `None`. Refactor `test_in_memory_store_enforces_one_time_use` and
  `test_factory_defaults_to_redis_backend` to call it, preserving each test's own args (`allow_non_production=True`
  for the in-memory store; `redis_client=_FakeRedis(), ttl_seconds=30, key="state-factory"`,
  `verifier="verifier-factory"` for the factory). No behavior change.

**AC-0 (Global gates / anti-weakening) — full suite still green, nothing weakened.**
- No assertions removed or relaxed, no new wall-clock sleeps, no edits to `pytest.ini`, `pyproject.toml`,
  `config/ci/*`, `.github/`, `.brooks-lint-history.json`, or any generated artifact.
- Whole-layer validation (fresh):
  - `python -m pytest services/layer4-agents/tests -o cache_dir=..\..\.tmp\pytest-cache-layer4 -m "not postgres and not requires_postgres and not docker and not integration and not e2e" -p no:randomly -q` → exit 0, no **new** failures vs. prior baseline (~548 passed / ~10 skipped).
  - `python -m pytest services/layer4-agents/tests --collect-only -q --strict-markers -p no:randomly` → exit 0 (3274 collected).
  - `LAYER4_REQUIRE_TESTCONTAINERS=1` + collect-only → still exits non-zero with the `UsageError` cited above (gate behavior unchanged — the new AC-3 test asserts it, it does not alter it); unset after.
  - `python scripts/ci/check_mypy_baseline.py --service-dir services/layer4-agents --baseline config/ci/mypy_baseline_layer4.json --paths src` → 0 errors.
  - Targeted files: `test_resilience.py`, `test_oidc_cleanup.py`, `test_messaging.py`,
    `test_health_tracker.py`, `test_oidc_state_store.py`, `test_skip_gate.py` pass under the same `-m unit` profile.

## Scope Boundaries

**In scope:**
- Edit: `services/layer4-agents/tests/test_resilience.py`, `test_oidc_cleanup.py`, `test_messaging.py`,
  `test_health_tracker.py`, `test_oidc_state_store.py`.
- Create: `services/layer4-agents/tests/test_skip_gate.py`.
- Minimal additive production seams, each documented and behavior-preserving:
  - `OIDCCleanupTask.running` property — `services/layer4-agents/src/layer4_agents/services/oidc_cleanup.py`.
  - `MessageRouter.get_agent_load(agent_id)` — `services/layer4-agents/src/layer4_agents/messaging/router.py`.
  - `CircuitBreaker.refresh_state()` — `services/layer4-agents/src/layer4_agents/resilience.py`.
- Comment-only documentation of the private handshake in `test_health_tracker.py` (or an equally small seam).
- Process artefacts under `.goals/brooks-t2a-t3-t4-t5-remediation/`.

**Out of scope:**
- Re-architecting `TokenBucket`, `CircuitBreaker`, `MessageRouter`, `OIDCCleanupTask`, or `HealthTracker`.
- Renaming or removing any existing public or private production member.
- Any change to `conftest.py` logic, CI workflows, baselines, thresholds, `.brooks-lint-history.json`,
  `pytest.ini`, `pyproject.toml`, or generated artifacts.
- Removing/reducing existing coverage in any test (all changes strengthen or are behavior-equivalent).
- Any change outside `services/layer4-agents`.

## Applicable Project Conventions

**Validation commands** (PowerShell; no `&&`/`||`; chain with `;` + `if ($?)`). Interpreter:
`$py = (& python scripts/ci/resolve_python.py).Trim()` → resolves to `python`. Do NOT run literal
`make test-layer4` on Windows (TMPDIR is POSIX-only).

```text
$py -m pytest services/layer4-agents/tests/test_resilience.py services/layer4-agents/tests/test_oidc_cleanup.py services/layer4-agents/tests/test_messaging.py services/layer4-agents/tests/test_health_tracker.py services/layer4-agents/tests/test_oidc_state_store.py services/layer4-agents/tests/test_skip_gate.py -o cache_dir=..\..\.tmp\pytest-cache-layer4 -m unit -p no:randomly -q
$py -m pytest services/layer4-agents/tests -o cache_dir=..\..\.tmp\pytest-cache-layer4 -m "not postgres and not requires_postgres and not docker and not integration and not e2e" -p no:randomly -q
$py -m pytest services/layer4-agents/tests --collect-only -q --strict-markers -p no:randomly
$env:LAYER4_REQUIRE_TESTCONTAINERS="1"; $py -m pytest services/layer4-agents/tests --collect-only -q -p no:randomly; Remove-Item Env:LAYER4_REQUIRE_TESTCONTAINERS
$py scripts/ci/check_mypy_baseline.py --service-dir services/layer4-agents --baseline config/ci/mypy_baseline_layer4.json --paths src
```

**Commit convention:** Builder: `type(scope): [B] description` (≤72 chars, imperative) + trailer
`Assisted-by: OpenAI:GPT-5.6 Luna`. Inspector: `chore(scope): [I] description` + trailer
`Assisted-by: OpenAI:GPT-5.6 Sol`. One commit per agent per iteration; process artefacts (goal.md,
status.json, inspector-feedback-N.md, summary.md) are included.

**Guidelines / rules:**
- `.goals/brooks-w1-s1-s2-remediation/goal.md` — prior goal conventions and validation history.
- `services/layer4-agents/tests/_wait_utils.py` — `wait_until` polling helper (reuse; no new sleeps).
- No destructive git (`git reset --hard`, `git rebase --abort`) unless explicitly authorized.
- Behavior-first test naming; keep `pytest.mark.unit` on all touched tests; tests must be deterministic.
- pnpm-only for JS work — not applicable (Python-only change).