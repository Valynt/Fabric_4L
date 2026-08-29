"""Contract tests for change-scoping the release-evidence bundle fan-out.

P1 recovery objective: heavyweight inherited jobs (six-image builds, live-stack
boot, SAST) must only run when the change can affect them, while the required
08-release-evidence aggregate is always emitted and a scope-skipped child is
admitted only via a --skip-safe confirmation that is the exact negation of the
child's own scope gate.

Invariants verified:
1. change-scope declares exactly the six outputs this workflow consumes and
   post-resolves them to 'true' on non-PR events (snapshot parity is preserved
   for push/schedule/workflow_dispatch).
2. Every gated fan-in job gates on a subset of those six outputs, and its
   SKIPSAFE_* env in aggregate-08 is the De Morgan negation of its gate.
3. supply-chain-policy-check inherits build-and-scan's fate via needs
   propagation (no independent gate) and shares build-and-scan's SKIPSAFE
   confirmation.
4. consolidate-bundle runs `if: always()` and is never --skip-safe flagged
   (the bundle generator records missing evidence as manifest gaps instead of
   failing), so a fully-scoped-out PR still emits the aggregate.
5. aggregate-08 stays `if: always()`, needs only real jobs, and every --skip-safe
   entry resolves to a real job with a matching env-backed confirmation.

These tests are wired into structural-preflight (ungated) so a future edit that
breaks skip-safety fails CI without depending on the merge gate to catch it.
"""
from __future__ import annotations

from pathlib import Path

from tests.ci._change_scope_contract import (
    aggregate_step,
    assert_post_resolve_outputs,
    job_outputs,
    job_steps,
    load_workflow,
    normalize_expr,
    parse_scope_expr,
    skip_safe_entries,
    workflow_job,
    workflow_jobs,
)

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/release-evidence-bundle.yml"
AGGREGATE_JOB = "aggregate-08-release-evidence"

# The six change-scope outputs this workflow actually consumes. Adding a new
# scope here requires also adding it to the change-scope job outputs and to
# every gate/SKIPSAFE pair below.
CHANGE_SCOPE_OUTPUTS = {
    "backend",
    "deps",
    "k8s",
    "release-policy",
    "ci-governance",
    "ci-tooling",
}

# job -> scope set its `if:` gate must reference (exactly).
GATED_JOBS = {
    "release-readiness-gate": {"k8s", "release-policy", "ci-governance", "ci-tooling"},
    "build-and-scan": {"backend", "deps", "ci-governance"},
    "sast-and-tests": {"backend"},
    "live-stack-evidence": {"backend", "deps", "ci-tooling"},
}

# job -> SKIPSAFE_* env name used to confirm its skip in aggregate-08.
SKIP_SAFE_ENVS = {
    "release-readiness-gate": "SKIPSAFE_RELEASE_READINESS",
    "build-and-scan": "SKIPSAFE_BUILD_AND_SCAN",
    "supply-chain-policy-check": "SKIPSAFE_SUPPLY_CHAIN_POLICY",
    "sast-and-tests": "SKIPSAFE_SAST_AND_TESTS",
    "live-stack-evidence": "SKIPSAFE_LIVE_STACK",
}

# Jobs that are never admissible-skip and therefore must never get a --skip-safe
# entry: change-scope always runs, consolidate-bundle always runs and its
# generator never fails on gaps.
UNSKIPPABLE = {"change-scope", "consolidate-bundle"}


def _load() -> dict[str, object]:
    return load_workflow(WORKFLOW)


def _aggregate(data: dict[str, object]) -> tuple[dict[str, object], str]:
    return aggregate_step(data, AGGREGATE_JOB)


def test_change_scope_job_exposes_exactly_the_consumed_outputs() -> None:
    data = _load()
    cs = workflow_job(data, "change-scope")
    outputs = job_outputs(cs)
    assert set(outputs) == CHANGE_SCOPE_OUTPUTS

    for scope in CHANGE_SCOPE_OUTPUTS:
        assert normalize_expr(str(outputs[scope])) == f"steps.scope.outputs.{scope}"

    # Non-PR events (push/schedule/workflow_dispatch) emit no diff; the
    # change-scope action fails open to 'true', and the Post-resolve step makes
    # that explicit so consumers never read an empty string as 'false'.
    post_resolve = "\n".join(
        str(step.get("run", ""))
        for step in job_steps(cs)
        if step.get("name") == "Post-resolve change scopes"
    )
    assert_post_resolve_outputs(post_resolve, CHANGE_SCOPE_OUTPUTS)


def test_gated_jobs_are_scope_gated_and_consume_change_scope() -> None:
    data = _load()
    for job_id, expected_scopes in GATED_JOBS.items():
        job = workflow_job(data, job_id)
        needs = job.get("needs")
        needs_list = needs if isinstance(needs, list) else ([needs] if needs else [])
        assert "change-scope" in needs_list, f"{job_id} does not need change-scope"

        gate = str(job.get("if", ""))
        clauses = parse_scope_expr(gate, "||", CHANGE_SCOPE_OUTPUTS)
        assert clauses, f"{job_id} has no change-scope gate"
        assert {s for s, _ in clauses} == expected_scopes
        assert all(v == "true" for _, v in clauses), (
            f"{job_id} gate must compare against 'true' (negation lives in the "
            "aggregate's SKIPSAFE env)"
        )


def test_supply_chain_policy_check_inherits_build_and_scan_skip() -> None:
    data = _load()
    job = workflow_job(data, "supply-chain-policy-check")
    # No independent gate: GitHub auto-skips it exactly when build-and-scan
    # skips (needs propagation), which keeps it from ever running with missing
    # scan artifacts. An independent gate here would be a correctness bug.
    assert not job.get("if"), (
        "supply-chain-policy-check must not have an independent scope gate; it "
        "consumes build-and-scan artifacts and must inherit its fate"
    )
    needs = job.get("needs")
    assert needs == ["build-and-scan"], (
        f"supply-chain-policy-check needs {needs}, expected ['build-and-scan']"
    )


def test_aggregate_skip_safe_env_is_exact_negation_of_each_gate() -> None:
    data = _load()
    env, run = _aggregate(data)

    for job_id, expected_scopes in GATED_JOBS.items():
        gate = str(workflow_job(data, job_id).get("if", ""))
        gate_scopes = {
            s for s, v in parse_scope_expr(gate, "||", CHANGE_SCOPE_OUTPUTS) if v == "true"
        }

        env_name = SKIP_SAFE_ENVS[job_id]
        assert env_name in env, f"aggregate-08 missing env {env_name}"
        env_expr = env[env_name]
        assert isinstance(env_expr, str)
        env_clauses = parse_scope_expr(env_expr, "&&", CHANGE_SCOPE_OUTPUTS)

        assert {s for s, _ in env_clauses} == gate_scopes == expected_scopes, (
            f"{job_id}: gate scopes {gate_scopes} != SKIPSAFE env scopes "
            f"{ {s for s, _ in env_clauses} } (expected {expected_scopes})"
        )
        assert all(v == "false" for _, v in env_clauses), (
            f"{job_id}: SKIPSAFE env must be the negation (== 'false') of its gate"
        )
        # Witness: De Morgan check that the flag is actually wired up.
        assert f"--skip-safe {job_id}={env_name}" in run, (
            f"{job_id} gate is gated but aggregate-08 lacks "
            f"--skip-safe {job_id}={env_name}"
        )


def test_supply_chain_skip_safe_confirmation_matches_build_and_scan() -> None:
    data = _load()
    env, run = _aggregate(data)
    supply_env = env["SKIPSAFE_SUPPLY_CHAIN_POLICY"]
    build_env = env["SKIPSAFE_BUILD_AND_SCAN"]
    assert isinstance(supply_env, str) and isinstance(build_env, str)
    assert normalize_expr(supply_env) == normalize_expr(build_env), (
        "SKIPSAFE_SUPPLY_CHAIN_POLICY must mirror SKIPSAFE_BUILD_AND_SCAN so the "
        "auto-skipped child is admitted exactly when build-and-scan is"
    )
    assert (
        "--skip-safe supply-chain-policy-check=SKIPSAFE_SUPPLY_CHAIN_POLICY" in run
    )


def test_unskippable_jobs_never_get_a_skip_safe_entry() -> None:
    data = _load()
    _, run = _aggregate(data)
    entries = skip_safe_entries(run)

    for job_id in UNSKIPPABLE:
        assert job_id not in entries, (
            f"{job_id} is unskippable-by-design but has a --skip-safe entry"
        )
    consolidate = workflow_job(data, "consolidate-bundle")
    assert consolidate.get("if") == "always()", (
        "consolidate-bundle must run on always() so a fully scoped-out PR still "
        "emits the aggregate"
    )


def test_aggregate_always_runs_and_every_skip_admission_is_confirmed() -> None:
    data = _load()
    jobs = workflow_jobs(data)
    agg = workflow_job(data, AGGREGATE_JOB)
    assert agg.get("if") == "always()", "aggregate-08 must be if: always()"

    needs = agg.get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    for child in needs:
        assert child in jobs, f"aggregate-08 needs unknown job {child}"

    _, run = _aggregate(data)
    entries = skip_safe_entries(run)

    names = set(SKIP_SAFE_ENVS.values())
    for job_id, env_name in entries.items():
        assert job_id in jobs, f"--skip-safe references unknown job {job_id}"
        assert env_name in names, f"--skip-safe references unknown env {env_name}"
        assert job_id not in UNSKIPPABLE

    # Every gated fan-in that could skip must have a confirmation; nothing else
    # may carry one.
    assert set(entries) == set(GATED_JOBS) | {"supply-chain-policy-check"}
