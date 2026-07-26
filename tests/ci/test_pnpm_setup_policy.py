from __future__ import annotations

import json
import re
from pathlib import Path

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
