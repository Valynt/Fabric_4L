from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "stack_health_check.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stack_health_check", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_stack_health_gate_covers_l1_to_l6_and_prefers_ready_where_defined() -> None:
    module = load_module()

    assert set(module.DEFAULT_ENDPOINTS) == {"layer1", "layer2", "layer3", "layer4", "layer5", "layer6"}
    assert module.DEFAULT_ENDPOINTS["layer2"][0].endswith(":8002/ready")
    assert module.DEFAULT_ENDPOINTS["layer6"][0].endswith(":8006/ready")
