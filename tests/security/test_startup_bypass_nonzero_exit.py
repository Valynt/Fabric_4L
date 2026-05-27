from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "services.layer1-ingestion.src.api.main",
        "services.layer3-knowledge.src.api.main",
        "services.layer4-agents.src.api.main",
        "services.layer6-benchmarks.src.api.main",
        "packages.shared.src.value_fabric.layer2.api.main",
    ],
)
def test_startup_rejects_bypass_flags_with_nonzero_exit(module_name: str) -> None:
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env["DEV_AUTH_BYPASS"] = "true"
    env["ALLOW_INSECURE_DEV_AUTH_BYPASS"] = "true"

    proc = subprocess.run(
        [sys.executable, "-c", f"import importlib; importlib.import_module('{module_name}')"],
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode != 0
    stderr = f"{proc.stdout}\n{proc.stderr}"
    assert "cannot enable auth bypass flags" in stderr
