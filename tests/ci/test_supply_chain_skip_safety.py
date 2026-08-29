"""Contract tests for change-scoping the supply-chain integrity fan-out.

P1 recovery objective: heavyweight security jobs (tools preflight, source SBOM
scan, dependency audit, license compliance) must only run when the change can
affect them, while the required 07-supply-chain-integrity aggregate is always
emitted and a scope-skipped child is admitted only via a --skip-safe
confirmation that is the exact negation of the child's own scope gate.

Invariants verified:
1. change-scope declares exactly the five outputs this workflow consumes and
   post-resolves them to 'true' on non-PR events.
2. Every gated fan-in job gates on a subset of those five outputs, and its
   SKIPSAFE_* env in aggregate-07 is the De Morgan negation of its gate.
3. dependency-audit and license-check share ci-tools-preflight's gate
   byte-for-byte because they inherit its container fate via needs
   propagation; one SKIPSAFE env confirms all three skips.
4. source-bom-scan's gate is independent (it has no container dependency) and
   carries its own SKIPSAFE env.
5. supply-chain-summary runs `if: always()`, admits success|skipped for the
   three scope-gated jobs, and still hard-requires release-image controls on
   dispatch/certify.
6. aggregate-07 stays `if: always()`, needs only real jobs, and every
   --skip-safe entry resolves to a real job with a matching env-backed
   confirmation; the image-cert jobs (sbom-scan, provenance,
   verify-signatures) are always covered by SKIPSAFE_IMAGE_CERT.

These tests are wired into structural-preflight (ungated) so a future edit that
breaks skip-safety fails CI without depending on the merge gate to catch it.
"""
from __future__ import annotations

from pathlib import Path

from tests.ci._change_scope_contract import (
    aggregate_step,
    assert_post_resolve_outputs,
    assert_scope_gates_semantic_equality,
    load_workflow,
    normalize_expr,
    parse_scope_expr,
    skip_safe_entries,
)

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/supply-chain-integrity.yml"
AGGREGATE_JOB = "aggregate-07-supply-chain-integrity"

# The five change-scope outputs this workflow actually consumes. Adding a new
# scope here requires also adding it to the change-scope job outputs and to
# every gate/SKIPSAFE pair below.
CHANGE_SCOPE_OUTPUTS = {
    "backend",
    "deps",
    "ci-global",
    "ci-tooling",
    "ci-governance",
}

# job -> scope set its `if:` gate must reference.
GATED_JOBS = {
    # Preflight boots the centrally managed tools container; the audit and
    # license jobs consume that same image, so all three share one gate and one
    # aggregate env handled by _SHARED_GATE_JOBS.
    "ci-tools-preflight": {"ci-global", "deps", "ci-tooling"},
    "source-sbom-scan": {"backend", "deps", "ci-governance", "ci-tooling"},
    "dependency-audit": {"ci-global", "deps", "ci-tooling"},
    "license-check": {"ci-global", "deps", "ci-tooling"},
}

# Jobs whose gate is semantically identical to ci-tools-preflight's (they consume the
# preflight-built container and inherit its fate via needs propagation). One
# SKIPSAFE env confirms all of them.
SHARED_GATE_JOBS = {"ci-tools-preflight", "dependency-audit", "license-check"}

# job -> SKIPSAFE_* env name used to confirm its skip in aggregate-07.
SKIP_SAFE_ENVS = {
    "ci-tools-preflight": "SKIPSAFE_PREFLIGHT",
    "dependency-audit": "SKIPSAFE_PREFLIGHT",
    "license-check": "SKIPSAFE_PREFLIGHT",
    "source-sbom-scan": "SKIPSAFE_SOURCE_SBOM",
}

# Release-image certification jobs: they only run on dispatch or when
# certify_images is requested, and are always admitted on PR/merge_group.
IMAGE_CERT_JOBS = {"sbom-scan", "provenance", "verify-signatures"}

# Jobs that never admit a change-scope skip: change-scope always runs, and
# supply-chain-summary always runs (it is the human-facing gate log).
UNSKIPPABLE = {"change-scope", "supply-chain-summary"}


def _load() -> dict[str, object]:
    return load_workflow(WORKFLOW)


def _aggregate(data: dict[str, object]) -> tuple[dict[str, object], str]:
    return aggregate_step(data, AGGREGATE_JOB)


def test_change_scope_job_exposes_exactly_the_consumed_outputs() -> None:
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    cs = jobs["change-scope"]  # type: ignore[index]
    outputs = cs.get("outputs")  # type: ignore[union-attr]
    assert outputs is not None, "change-scope job missing outputs block"
    assert set(outputs) == CHANGE_SCOPE_OUTPUTS

    for scope in CHANGE_SCOPE_OUTPUTS:
        assert normalize_expr(outputs[scope]) == f"steps.scope.outputs.{scope}"

    # Non-PR events (push/schedule/workflow_dispatch) emit no diff; the
    # change-scope action fails open to 'true', and the Post-resolve step makes
    # that explicit so consumers never read an empty string as 'false'.
    post_resolve = "\n".join(
        str(step.get("run", ""))
        for step in cs["steps"]  # type: ignore[union-attr]
        if step.get("name") == "Post-resolve change scopes"
    )
    assert_post_resolve_outputs(post_resolve, CHANGE_SCOPE_OUTPUTS)


def test_gated_jobs_are_scope_gated_and_consume_change_scope() -> None:
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    for job_id, expected_scopes in GATED_JOBS.items():
        job = jobs[job_id]  # type: ignore[index]
        needs = job.get("needs")
        needs_list = needs if isinstance(needs, list) else ([needs] if needs else [])
        assert "change-scope" in needs_list, f"{job_id} does not need change-scope"

        gate = job.get("if", "")
        clauses = parse_scope_expr(gate, "||", CHANGE_SCOPE_OUTPUTS)
        assert clauses, f"{job_id} has no change-scope gate"
        assert {s for s, _ in clauses} == expected_scopes
        assert all(v == "true" for _, v in clauses), (
            f"{job_id} gate must compare against 'true' (negation lives in the "
            "aggregate's SKIPSAFE env)"
        )


def test_shared_gate_jobs_use_byte_identical_gate_and_one_env() -> None:
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    preflight_gate = jobs["ci-tools-preflight"].get("if", "")  # type: ignore[index]
    assert preflight_gate, "ci-tools-preflight has no gate"

    for job_id in SHARED_GATE_JOBS - {"ci-tools-preflight"}:
        target_gate = jobs[job_id].get("if", "")  # type: ignore[index]
        assert_scope_gates_semantic_equality(
            target_gate, preflight_gate, CHANGE_SCOPE_OUTPUTS, "||"
        )
        needs = jobs[job_id].get("needs")  # type: ignore[index]
        needs_list = needs if isinstance(needs, list) else ([needs] if needs else [])
        assert "ci-tools-preflight" in needs_list, (
            f"{job_id} must need ci-tools-preflight (container inheritance)"
        )


def test_aggregate_skip_safe_env_is_exact_negation_of_each_gate() -> None:
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    env, run = _aggregate(data)

    for job_id, expected_scopes in GATED_JOBS.items():
        gate = jobs[job_id].get("if", "")  # type: ignore[index]
        gate_scopes = {
            s for s, v in parse_scope_expr(gate, "||", CHANGE_SCOPE_OUTPUTS) if v == "true"
        }

        env_name = SKIP_SAFE_ENVS[job_id]
        assert env_name in env, f"aggregate-07 missing env {env_name}"
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
            f"{job_id} gate is gated but aggregate-07 lacks "
            f"--skip-safe {job_id}={env_name}"
        )


def test_source_sbom_env_is_independent_of_shared_gate() -> None:
    """source-bom-scan has no container dependency; it must confirm its own skip
    via SKIPSAFE_SOURCE_SBOM rather than borrowing the shared env."""
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    needs = jobs["source-sbom-scan"].get("needs")  # type: ignore[index]
    needs_list = needs if isinstance(needs, list) else ([needs] if needs else [])
    assert "ci-tools-preflight" not in needs_list, (
        "source-sbom-scan must not depend on the tools container"
    )
    env, run = _aggregate(data)
    assert isinstance(env.get("SKIPSAFE_SOURCE_SBOM"), str)
    assert "--skip-safe source-sbom-scan=SKIPSAFE_SOURCE_SBOM" in run
    assert "--skip-safe source-sbom-scan=SKIPSAFE_PREFLIGHT" not in run


def test_image_cert_jobs_are_gated_by_dispatch_and_confirmed() -> None:
    data = _load()
    env, run = _aggregate(data)
    assert isinstance(env.get("SKIPSAFE_IMAGE_CERT"), str)
    for job_id in IMAGE_CERT_JOBS:
        assert f"--skip-safe {job_id}=SKIPSAFE_IMAGE_CERT" in run, (
            f"{job_id} missing --skip-safe {job_id}=SKIPSAFE_IMAGE_CERT"
        )


def test_summary_admits_scope_skips_but_hard_requires_image_controls() -> None:
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    summary = jobs["supply-chain-summary"]  # type: ignore[index]
    assert summary.get("if") == "always()", "supply-chain-summary must be always()"

    steps = summary["steps"]  # type: ignore[union-attr]
    validate = next(
        step for step in steps if step.get("name") == "Validate prerequisite results"
    )
    run = validate.get("run", "")
    assert isinstance(run, str)
    # The loop admits success|skipped for every gated child, so a scoped skip
    # does not fail the summary.
    assert "success|skipped" in run
    summary_needs = {
        "source-sbom-scan",
        "sbom-scan",
        "provenance",
        "verify-signatures",
        "dependency-audit",
        "license-check",
    }
    for job_id in summary_needs:
        assert f"${{{{ needs.{job_id}.result }}}}" in run
    # Dispatch/manual certification still hard-requires release-image controls.
    assert 'if [ "${{ github.event_name }}" = "workflow_dispatch" ]' in run
    assert '[ "${{ inputs.certify_images }}" = "true" ]' in run
    assert "exit 1" in run


def test_unskippable_jobs_never_get_a_skip_safe_entry() -> None:
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    _, run = _aggregate(data)
    entries = skip_safe_entries(run)

    for job_id in UNSKIPPABLE:
        assert job_id not in entries, (
            f"{job_id} is unskippable-by-design but has a --skip-safe entry"
        )
    assert jobs["supply-chain-summary"].get("if") == "always()", (  # type: ignore[index]
        "supply-chain-summary must run on always() so a fully scoped-out PR still "
        "emits the aggregate"
    )


def test_aggregate_always_runs_and_every_skip_admission_is_confirmed() -> None:
    data = _load()
    jobs = data["jobs"]  # type: ignore[index]
    agg = jobs[AGGREGATE_JOB]  # type: ignore[index]
    assert agg.get("if") == "always()", "aggregate-07 must be if: always()"

    needs = agg.get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    for child in needs:
        assert child in jobs, f"aggregate-07 needs unknown job {child}"

    _, run = _aggregate(data)
    entries = skip_safe_entries(run)

    names = set(SKIP_SAFE_ENVS.values()) | {"SKIPSAFE_IMAGE_CERT"}
    for job_id, env_name in entries.items():
        assert job_id in jobs, f"--skip-safe references unknown job {job_id}"
        assert env_name in names, f"--skip-safe references unknown env {env_name}"
        assert job_id not in UNSKIPPABLE

    # Every gated fan-in and every release-image cert job has a confirmation;
    # nothing else may carry one.
    assert set(entries) == set(GATED_JOBS) | IMAGE_CERT_JOBS