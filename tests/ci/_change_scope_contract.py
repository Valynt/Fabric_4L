"""Shared contract-test helpers and invariants for change-scoped workflows.

Used across workflow skip-safety suites (e.g. supply-chain integrity, release
evidence) to eliminate duplicate scaffolding and provide semantic,
formatting-resilient assertions.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import yaml

# Matches a single change-scope output comparison clause.
# Resilient to whitespace variations around '==' and single vs double quotes.
SCOPE_CLAUSE = re.compile(
    r"^needs\.change-scope\.outputs\.([a-z0-9-]+)\s*==\s*['\"](\w+)['\"]$"
)

# Regex matching post-resolve echo statements in shell steps.
POST_RESOLVE_ECHO = re.compile(
    r"echo\s+['\"]?([a-z0-9-]+)=true['\"]?\s*>>\s*(\$GITHUB_OUTPUT|\$\{GITHUB_OUTPUT\})"
)


def load_workflow(path: Path) -> dict[str, object]:
    """Load and parse a GitHub Actions workflow YAML file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"Workflow at {path} must parse to a dict"
    return cast(dict[str, object], data)


def job_steps(job: dict[str, object]) -> list[dict[str, object]]:
    """Extract a safely-typed list of steps from a workflow job."""
    steps = job.get("steps", [])
    assert isinstance(steps, list), f"workflow job steps must be a list, got {type(steps)}"
    return cast(list[dict[str, object]], steps)


def job_outputs(job: dict[str, object]) -> dict[str, object]:
    """Extract a safely-typed outputs mapping from a workflow job."""
    outputs = job.get("outputs", {})
    assert isinstance(outputs, dict), "workflow job outputs must be a dict"
    return cast(dict[str, object], outputs)


def normalize_expr(expr: str) -> str:
    """Normalize a GitHub Actions expression by stripping interpolation wrappers
    and standardizing whitespace."""
    expr = expr.strip()
    if expr.startswith("${{") and expr.endswith("}}"):
        expr = expr[3:-2].strip()
    return re.sub(r"\s+", " ", expr)


def parse_scope_expr(
    expr: str,
    joiner: str,
    allowed_outputs: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Parse a change-scope gate (joiner '||') or SKIPSAFE env (joiner '&&')
    into (scope, expected_value) pairs, rejecting any non change-scope clause."""
    clean_expr = normalize_expr(expr)
    out: list[tuple[str, str]] = []
    for clause in clean_expr.split(joiner):
        clause = clause.strip()
        if not clause:
            continue
        match = SCOPE_CLAUSE.fullmatch(clause)
        assert match, f"expression contains a non change-scope clause: {clause!r}"
        scope, value = match.group(1), match.group(2)
        if allowed_outputs is not None:
            assert (
                scope in allowed_outputs
            ), f"scope {scope!r} is not in declared change-scope outputs: {allowed_outputs}"
        out.append((scope, value))
    return out


def workflow_jobs(data: dict[str, object]) -> dict[str, object]:
    """Extract a safely-typed jobs mapping from a loaded workflow."""
    jobs = data.get("jobs", {})
    assert isinstance(jobs, dict), "workflow must contain a jobs mapping"
    return cast(dict[str, object], jobs)


def workflow_job(data: dict[str, object], job_id: str) -> dict[str, object]:
    """Extract one safely-typed workflow job by id."""
    jobs = workflow_jobs(data)
    assert job_id in jobs, f"Workflow missing job: {job_id}"
    job = jobs[job_id]
    assert isinstance(job, dict), f"job {job_id} must be a dict"
    return cast(dict[str, object], job)


def aggregate_step(
    data: dict[str, object],
    aggregate_job_id: str,
    script_name: str = "aggregate_gate.py",
) -> tuple[dict[str, object], str]:
    """Return (env, run) of the aggregate step inside the specified aggregate job."""
    jobs = workflow_jobs(data)
    assert aggregate_job_id in jobs, f"Workflow missing aggregate job: {aggregate_job_id}"
    job = jobs[aggregate_job_id]
    assert isinstance(job, dict), f"aggregate job {aggregate_job_id} must be a dict"
    steps = job_steps(job)
    for step in steps:
        run = step.get("run", "")
        if isinstance(run, str) and script_name in run:
            env = step.get("env", {})
            assert isinstance(env, dict), f"step env in {aggregate_job_id} must be a dict"
            return cast(dict[str, object], env), run
    raise AssertionError(f"{aggregate_job_id} has no step executing {script_name}")


def skip_safe_entries(run: str) -> dict[str, str]:
    """Parse `--skip-safe JOB=ENV` flags from the aggregate run script block."""
    entries: dict[str, str] = {}
    for line in run.splitlines():
        line = line.strip()
        if not line.startswith("--skip-safe"):
            continue
        rest = line.removeprefix("--skip-safe").strip()
        job, _, env_name = rest.partition("=")
        assert "=" in line and env_name, f"malformed --skip-safe entry: {line}"
        # Drop a trailing shell line-continuation backslash
        env_name = env_name.rstrip()
        if env_name.endswith("\\"):
            env_name = env_name[:-1].rstrip()
        entries[job.strip()] = env_name.strip()
    return entries


def assert_post_resolve_outputs(post_resolve_run: str, expected_scopes: set[str]) -> None:
    """Assert that post-resolve step exports '{scope}=true' for every expected scope."""
    found_scopes = set()
    for match in POST_RESOLVE_ECHO.finditer(post_resolve_run):
        found_scopes.add(match.group(1))
    missing = expected_scopes - found_scopes
    assert not missing, f"Post-resolve step missing outputs for scopes: {missing}"


def assert_scope_gates_semantic_equality(
    gate_a: str,
    gate_b: str,
    allowed_outputs: set[str],
    joiner: str = "||",
) -> None:
    """Assert that two gate expressions represent the exact same semantic condition,
    independent of clause ordering or spacing."""
    clauses_a = set(parse_scope_expr(gate_a, joiner, allowed_outputs))
    clauses_b = set(parse_scope_expr(gate_b, joiner, allowed_outputs))
    assert clauses_a == clauses_b, (
        f"Gate expressions do not match semantically:\n"
        f"  A: {clauses_a}\n"
        f"  B: {clauses_b}"
    )
