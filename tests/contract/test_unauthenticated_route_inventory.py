from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

os.environ.setdefault("CONTRACT_TEST_MODE", "mock")

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "check_route_auth_inventory.py"


def test_unauthenticated_route_inventory_uses_repo_relative_paths() -> None:
    generated = REPO_ROOT / ".tmp" / "unauthenticated-route-inventory.generated.json"
    generated.parent.mkdir(exist_ok=True)
    try:
        result = subprocess.run(
            ["python", str(SCRIPT), "--inventory-json", str(generated)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        inventory = json.loads(generated.read_text(encoding="utf-8"))
    finally:
        generated.unlink(missing_ok=True)

    for route in inventory:
        assert route["auth_present"] is False
        assert not Path(route["source"]).is_absolute()
        assert "/workspace/" not in route["source"]
        assert route["allowlisted"] or route["system_endpoint"]
