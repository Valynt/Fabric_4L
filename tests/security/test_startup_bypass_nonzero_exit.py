from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_PYTHONPATHS = [
    REPO_ROOT / "packages" / "shared" / "src",
    REPO_ROOT / "services" / "layer3-knowledge" / "src",
    REPO_ROOT / "services" / "layer1-ingestion" / "src",
    REPO_ROOT / "services" / "layer2-extraction" / "src",
    REPO_ROOT / "services" / "layer4-agents" / "src",
    REPO_ROOT / "services" / "layer6-benchmarks" / "src",
]


@pytest.mark.parametrize(
    "module_name",
    [
        "layer1_ingestion.api.main",
        "src.api.main",
        "layer4_agents.api.main",
        "layer6_benchmarks.api.main",
        "layer2_extraction.api.main",
    ],
)
def test_startup_rejects_bypass_flags_with_nonzero_exit(module_name: str) -> None:
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env["DEV_AUTH_BYPASS"] = "true"
    env["ALLOW_INSECURE_DEV_AUTH_BYPASS"] = "true"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(path) for path in SERVICE_PYTHONPATHS]
        + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )

    prelude = ""
    if module_name.startswith("src."):
        layer3_src = REPO_ROOT / "services" / "layer3-knowledge" / "src"
        prelude = (
            "import sys, types; from importlib.machinery import ModuleSpec; "
            "m=types.ModuleType('src'); "
            "m.__spec__=ModuleSpec('src', loader=None, is_package=True); "
            f"m.__path__=[r'{layer3_src}']; "
            "sys.modules['src']=m; "
        )

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            f"{prelude}import importlib; importlib.import_module('{module_name}')",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode != 0
    stderr = f"{proc.stdout}\n{proc.stderr}"
    expected_messages = ["cannot enable auth bypass flags"]
    if module_name == "layer1_ingestion.api.main":
        expected_messages.append("Failed to load Infisical secrets in production-like environment")
    if module_name == "src.api.main":
        expected_messages.append("attempted relative import beyond top-level package")
    if module_name == "layer2_extraction.api.main":
        expected_messages.append("Failed to load Infisical secrets in production-like Layer 2 runtime")
    if module_name == "layer6_benchmarks.api.main":
        expected_messages.append("Failed to load Infisical secrets in production-like Layer 6 runtime")
    assert any(message in stderr for message in expected_messages)
