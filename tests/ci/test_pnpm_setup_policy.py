from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def test_package_json_scripts_do_not_invoke_pnpm_through_corepack() -> None:
    """Scripts must use the repository-installed pnpm directly, not corepack."""
    for pkg_path in REPO_ROOT.rglob("package.json"):
        # Skip dependency caches that may have been copied into the tree.
        if "node_modules" in pkg_path.parts:
            continue
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        for name, script in pkg.get("scripts", {}).items():
            assert isinstance(script, str)
            assert "corepack pnpm" not in script, (
                f"{pkg_path} script '{name}' invokes pnpm through corepack; "
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
