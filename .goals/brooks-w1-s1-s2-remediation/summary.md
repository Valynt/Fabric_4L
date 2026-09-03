# Goal Summary — brooks-w1-s1-s2-remediation

**Goal:** remediate the three brooks-test review findings in
`services/layer4-agents` with the smallest cohesive changes — no weakened
tests, baselines, thresholds, generated artifacts, or CI behavior.

**Result:** **completed in 1 iteration** — Builder commit `88aef94c7`,
Independent-verification PASS (orchestrator fallback, see below).

## What was achieved (per acceptance criterion)

| # | Criterion | Achievement |
|---|---|---|
| A1 | Fail closed when env-gated coverage is required | `LAYER4_REQUIRE_TESTCONTAINERS=1` now raises `pytest.UsageError` (exit 4) citing VF-SKIP-119/VF-SKIP-120 instead of silently skipping |
| A2 | Skip transparency | Config-time `RuntimeWarning: Skipped 30 Docker/testcontainers-gated test item(s)...` names the count and the escape hatch (`LAYER4_REQUIRE_TESTCONTAINERS=1` or `make test-layer4-live`) |
| A3 | No skip-weakening | Skip-guard lines byte-identical; `check_pytest_skip_governance.py` → 0 violations |
| A4 | No wall-clock expiry tests | OIDC expiry tests use `_FrozenDateTime`/`_FakeRedis` virtual clocks; both expired-denial and valid-consumption paths asserted |
| A5 | Timeout contract retained | `SlowTool` latency sims 1.0s→0.05s (> 0.01s timeout), comment-documented; timeout still exercises deterministically |
| A6 | Targeted tests pass | 146 passed across the 7 changed test files (exit 0) |
| A7 | No new full-profile failures | Only 2 failures, both pre-existing and A/B-proven at parent (missing `docx` module; audit smoke exceeding wall-clock timeout) |
| A8 | Marker registry aligned | `--strict-markers` in `pyproject.toml` addopts; `--collect-only --strict-markers` = 3274 tests, exit 0 (S2 not a scaffolding hack) |
| A9 | Type-check baseline stable | mypy 0 errors, baseline 0 |

## Iteration history

- **Iteration 1** — Builder implemented all three remediations in one
  commit and verified internally. Inspector returned **PASS**.

## Key issue & resolution

The official `Goal: Inspector` subagent returned empty transcripts on
three attempts (sync, background, and a wake-up message). Per the skill
protocol, the orchestrator performed the independent verification from
scratch — re-running every gate (A1–A9) fresh against HEAD, plus a
diff-level anti-weakening audit (no new wall-clock sleeps, no removed
assertions, no baseline/threshold/CI edits, no generated artifacts).
Feedback recorded in `inspector-feedback-1.md`.

## Recommendations for the project

- The two pre-existing full-profile failures deserve their own follow-up
  tickets: install `python-docx` for the generation-contract test, and
  either split the audit-orchestrator smoke audit or raise its timeout.
- Investigate why the `goal-inspector` subagent emits empty transcripts
  — the orchestrator fallback works but loses the "fresh context"
  independence the skill is designed for.
- Consider applying the skip-transparency pattern (A1/A2) to the other
  layer services that still gate tests on Docker/testcontainers.

## Squash command

```
git reset --soft 895cfd9637a5dcc14eb71ffa6566ea082776f357
git commit -m 'test(layer4): harden env-gated skips, determinize test time, strict markers' -m 'Silent environment-gated test skips in layer4 are now loud: they warn at config time with a skip count and an escape hatch, and fail closed when the user explicitly demands the Docker/Postgres lane. Wall-clock sleeps in expiry and circuit-breaker tests are replaced with deterministic virtual clocks and predicate polling, so the suite no longer depends on timing luck. The pytest marker registry is now strict, so any marker drift fails collection instead of being silently tolerated.' -m 'Assisted-by: OpenAI:GPT-5.6 Luna'
```

Push / PR remains the user's decision (branch `valyntxyz-verbose-carnival`,
no upstream configured).