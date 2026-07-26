from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def test_package_json_scripts_do_not_invoke_pnpm_through_corepack() -> None:
    """Scripts must use the repository-installed pnpm directly, not corepack."""
    corepack_pnpm = re.compile(r"\bcorepack\s+pnpm\b")
    import subprocess

    package_json_files = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT, text=True).splitlines()

    for rel_path in package_json_files:
        if not rel_path.endswith("package.json"):
            continue

        entry = REPO_ROOT / rel_path
        pkg = json.loads(entry.read_text(encoding="utf-8"))
        for name, script in pkg.get("scripts", {}).items():
            assert isinstance(script, str)
            assert not corepack_pnpm.search(script), (
                f"{entry} script '{name}' invokes pnpm through corepack; "
                "use plain 'pnpm' instead"
            )


def test_workflows_use_supported_pnpm_action_setup() -> None:
    """Workflows must not use unsupported pnpm/action-setup versions."""
    unsupported = re.compile(r"pnpm/action-setup@v2(?:\.\d+)?\b")
    violations: list[str] = []
    for wf_path in WORKFLOWS_DIR.glob("*.yml"):
        for idx, line in enumerate(wf_path.read_text(encoding="utf-8").splitlines(), start=1):
            if unsupported.search(line):
                violations.append(f"{wf_path}:{idx}: {line.strip()}")
    assert not violations, "Unsupported pnpm/action-setup versions found:\n" + "\n".join(
        violations
    )


def test_setup_node_pnpm_cache_runs_after_pnpm_setup() -> None:
    """setup-node pnpm caching requires pnpm/action-setup to run first."""
    violations: list[str] = []

    for wf_path in WORKFLOWS_DIR.glob("*.yml"):
        workflow = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        if not isinstance(workflow, dict):
            continue
        jobs = workflow.get("jobs", {})
        if not isinstance(jobs, dict):
            continue

        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            pnpm_setup_seen = False
            for step in job.get("steps", []):
                if not isinstance(step, dict):
                    continue

                uses = str(step.get("uses", ""))
                if uses.startswith("pnpm/action-setup@"):
                    pnpm_setup_seen = True

                with_config = step.get("with") or {}
                if (
                    uses.startswith("actions/setup-node@")
                    and isinstance(with_config, dict)
                    and with_config.get("cache") == "pnpm"
                    and not pnpm_setup_seen
                ):
                    violations.append(f"{wf_path.name}:{job_name}")

    assert not violations, (
        "setup-node pnpm cache appears before pnpm setup in: " + ", ".join(violations)
    )
