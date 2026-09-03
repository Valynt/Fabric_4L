"""Canonical architecture-governance aggregate (``make check-governance``).

Composes the resident architecture checks into a single deterministic run that
emits one uniform, machine-readable verdict envelope and a single exit code.
It reuses — and does not reimplement — the existing ratchet/boundary/ownership
scripts, so those stay authoritative.

Composed logical checks
-----------------------
* ``check-import-cycles``          -> ``structural_fitness_ratchet.py``
* ``check-architecture-boundaries`` -> ``check_model_provider_boundaries.py``
* ``check-ownership-registry``      -> shared-import enforcement, public-import
                                       policy, canonical-import registry, and
                                       backend platform-validation ownership.
* ``check-shared-duplication``      -> ``check_shared_duplication.py`` (scoped
                                       DRY ratchet for ``packages/shared``).
* ``check-governance-baseline``     -> type-escape ratchet + a deterministic
                                       "baseline is regenerable" check for the
                                       duplication baseline.

Each sub-check yields ``status`` in ``pass | fail | error``. ``error``
means the check itself could not run (missing script, Python traceback, or
timeout) rather than a discovered violation.

Outputs
-------
* ``artifacts/governance/check-governance.json`` — machine-readable envelope.
* ``artifacts/governance/check-governance.md``   — human-readable summary.

Exit codes
----------
0  every sub-check passed.
1  at least one sub-check failed (violation), none errored.
2  at least one sub-check errored (runner problem).

Determinism: the verdict depends only on the working tree and the checked-in
baselines — no LLM, no network, no wall-clock in the envelope.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "governance"
PY = sys.executable

CHECK_ID = "check-governance"
CHECK_NAME = "Architecture Governance"
SCHEMA_VERSION = 1
OVERALL_SCOPE = "platform architecture: import topology, boundaries, ownership, shared-package DRY"

TIMEOUT_SECONDS = 600
MAX_OUTPUT_CHARS = 4000


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------
def _status_from_exit(exit_code: int | None, stderr: str) -> str:
    if exit_code == 0:
        return "pass"
    if "Traceback (most recent call last)" in stderr:
        return "error"
    if exit_code == 1:
        return "fail"
    # Any other non-zero exit code (e.g. argparse usage errors, which exit 2)
    # indicates the check itself could not run cleanly, not a discovered
    # violation — classify as error to fail closed.
    return "error"


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… ({len(text) - limit} more chars)"


def run_argv(argv: list[str], timeout: int = TIMEOUT_SECONDS) -> dict:
    """Run one sub-check command and normalize its outcome into a dict."""
    command = " ".join(argv)
    try:
        proc = subprocess.run(
            argv,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        output = _truncate((proc.stdout + "\n" + proc.stderr).strip())
        return {
            "command": command,
            "status": _status_from_exit(proc.returncode, proc.stderr),
            "exit_code": proc.returncode,
            "output": output,
        }
    except FileNotFoundError:
        return {
            "command": command,
            "status": "error",
            "exit_code": None,
            "output": f"command not found: {argv[0]}",
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "status": "error",
            "exit_code": None,
            "output": f"timed out after {timeout}s",
        }


def _aggregate(results: list[dict]) -> str:
    """Aggregate per-command statuses with precedence error > fail > pass."""
    if any(r["status"] == "error" for r in results):
        return "error"
    if any(r["status"] == "fail" for r in results):
        return "fail"
    return "pass"


# ---------------------------------------------------------------------------
# Sub-check specifications
# ---------------------------------------------------------------------------
def _script(*argv: str) -> list[str]:
    return [PY, *argv]


def build_specs() -> list[dict]:
    return [
        {
            "check_id": "check-import-cycles",
            "name": "Import cycles / structural fitness ratchet",
            "scope": "packages + services (module size, complexity, import cycles)",
            "baseline": "config/ci/structural_fitness_baseline.json",
            "commands": [_script("scripts/ci/structural_fitness_ratchet.py")],
        },
        {
            "check_id": "check-architecture-boundaries",
            "name": "Architecture boundary ratchet (model/provider gateway)",
            "scope": "services (provider gateway allowlist)",
            "baseline": None,
            "commands": [
                _script("scripts/ci/check_model_provider_boundaries.py"),
            ],
        },
        {
            "check_id": "check-ownership-registry",
            "name": "Ownership / canonical-import registry",
            "scope": "packages + services (shared imports, public API, canonical paths)",
            "baseline": None,
            "commands": [
                _script(
                    "scripts/ci/check_shared_imports.py",
                    "--strict",
                    "--scope",
                    "executable",
                ),
                _script("scripts/ci/check_value_fabric_public_imports.py"),
                _script("scripts/ci/check_runtime_canonical_imports.py", "--strict"),
                _script("scripts/ci/check_shared_identity_canonical_imports.py"),
                _script("scripts/ci/assert_backend_platform_validation_ownership.py"),
            ],
        },
        {
            "check_id": "check-shared-duplication",
            "name": "Shared-package DRY (duplication) ratchet",
            "scope": "packages/shared/src/value_fabric/shared/",
            "baseline": "config/ci/shared_duplication_baseline.json",
            "commands": [
                _script(
                    "scripts/ci/check_shared_duplication.py",
                    "--json",
                    str(ARTIFACT_DIR / "check-shared-duplication.json"),
                ),
            ],
        },
        {
            "check_id": "check-governance-baseline",
            "name": "Governance baselines (type escapes + duplication regenerable)",
            "scope": "packages + services + packages/shared",
            "baseline": "config/ci/type_escape_baseline.json",
            "commands": [_script("scripts/ci/type_escape_ratchet.py")],
        },
    ]


# ---------------------------------------------------------------------------
# Specialized sub-check results
# ---------------------------------------------------------------------------
def _read_dup_envelope() -> dict | None:
    path = ARTIFACT_DIR / "check-shared-duplication.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _duplication_regenerable(runner) -> dict:
    checked_in = REPO_ROOT / "config/ci/shared_duplication_baseline.json"
    label = "check_shared_duplication.py --update (regenerable)"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            regenerated = Path(tmp) / "shared_duplication_baseline.json"
            run = runner(
                _script(
                    "scripts/ci/check_shared_duplication.py",
                    "--update",
                    "--baseline",
                    str(regenerated),
                )
            )
            if run["status"] != "pass":
                return {
                    "command": label,
                    "status": run["status"],
                    "exit_code": run.get("exit_code"),
                    "output": run["output"],
                }
            try:
                current = checked_in.read_text(encoding="utf-8")
                rebuilt = regenerated.read_text(encoding="utf-8")
            except OSError as exc:  # pragma: no cover - defensive
                return {
                    "command": label,
                    "status": "error",
                    "exit_code": None,
                    "output": str(exc),
                }
            if current != rebuilt:
                return {
                    "command": label,
                    "status": "fail",
                    "exit_code": 1,
                    "output": (
                        "config/ci/shared_duplication_baseline.json is stale; "
                        "regenerate it with `python scripts/ci/check_shared_duplication.py --update`."
                    ),
                }
            return {
                "command": label,
                "status": "pass",
                "exit_code": 0,
                "output": "shared_duplication_baseline.json is regenerable (no drift).",
            }
    except OSError as exc:  # pragma: no cover - defensive
        return {"command": label, "status": "error", "exit_code": None, "output": str(exc)}


def _baseline_present(baseline: str | None) -> bool:
    return bool(baseline) and (REPO_ROOT / baseline).exists()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def run_governance(runner=run_argv, only: str | None = None) -> dict:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    sub_checks: list[dict] = []

    specs = build_specs()
    if only is not None:
        specs = [s for s in specs if s["check_id"] == only]
        if not specs:
            raise ValueError(f"unknown check id: {only}")

    for spec in specs:
        results = [runner(cmd) for cmd in spec["commands"]]

        if spec["check_id"] == "check-shared-duplication":
            env = _read_dup_envelope()
            if env is not None:
                status = env.get("status", results[0]["status"])
                baseline_present = bool(env.get("baseline_present", False))
                violations = env.get("violations", [])
            else:
                status = results[0]["status"]
                baseline_present = False
                violations = []
        elif spec["check_id"] == "check-governance-baseline":
            results.append(_duplication_regenerable(runner))
            status = _aggregate(results)
            baseline_present = _baseline_present(spec["baseline"])
            violations = []
        else:
            status = _aggregate(results)
            baseline_present = _baseline_present(spec["baseline"])
            violations = []

        sub_checks.append(
            {
                "check_id": spec["check_id"],
                "name": spec["name"],
                "scope": spec["scope"],
                "status": status,
                "baseline_present": baseline_present,
                "details": results,
                "violations": violations,
            }
        )

    status = _aggregate([{"status": sc["status"]} for sc in sub_checks])
    return {
        "check_id": CHECK_ID,
        "name": CHECK_NAME,
        "schema_version": SCHEMA_VERSION,
        "scope": OVERALL_SCOPE,
        "status": status,
        "sub_checks": sub_checks,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def render_markdown(report: dict) -> str:
    lines = [f"# {report['name']}", "", f"**Status:** {report['status'].upper()}", ""]
    lines.append("| Check | Status | Baseline |")
    lines.append("| --- | --- | --- |")
    for sc in report["sub_checks"]:
        lines.append(
            f"| {sc['check_id']} | {sc['status']} | "
            f"{'yes' if sc['baseline_present'] else 'no'} |"
        )
    lines.append("")
    for sc in report["sub_checks"]:
        if sc["status"] == "pass":
            continue
        lines.append(f"## {sc['check_id']} — {sc['status'].upper()}")
        if sc["violations"]:
            lines.append("")
            for v in sc["violations"]:
                lines.append(f"- {v.get('message', v)}")
            lines.append("")
        for detail in sc["details"]:
            if detail["status"] == "pass":
                continue
            lines.append(f"### `{detail['command']}`")
            lines.append("")
            lines.append("```")
            lines.append(detail["output"])
            lines.append("```")
            lines.append("")
    return "\n".join(lines) + "\n"


def _print_report(report: dict) -> None:
    print(f"{report['name']}: {len(report['sub_checks'])} sub-checks")
    for sc in report["sub_checks"]:
        print(f"  [{sc['status']:5}] {sc['check_id']}")
    print(f"Result: {report['status'].upper()}")


def _exit_code_for(status: str) -> int:
    return {"pass": 0, "fail": 1, "error": 2}[status]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical architecture-governance aggregate."
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=ARTIFACT_DIR / "check-governance.json",
        help="Write the machine-readable envelope here.",
    )
    parser.add_argument(
        "--md",
        type=Path,
        default=ARTIFACT_DIR / "check-governance.md",
        help="Write the human-readable summary here.",
    )
    parser.add_argument(
        "--check",
        default=None,
        help="Run only the named sub-check (e.g. check-shared-duplication).",
    )
    args = parser.parse_args(argv)

    report = run_governance(only=args.check)

    json_path = args.json if args.json.is_absolute() else REPO_ROOT / args.json
    md_path = args.md if args.md.is_absolute() else REPO_ROOT / args.md
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")

    _print_report(report)
    return _exit_code_for(report["status"])


if __name__ == "__main__":
    raise SystemExit(main())
