from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "mandatory_security_regression_gate.sh"

REQUIRED = [
    "tests/shared/identity/test_api_key_resolver_hostile_suite.py",
    "services/layer1-ingestion/tests/test_api_key_resolver_hostile_cases.py",
    "services/layer2-extraction/tests/test_api_key_resolver_hostile_cases.py",
]


def test_hostile_suite_wired_for_migrated_layers() -> None:
    script = GATE_SCRIPT.read_text(encoding="utf-8")
    for rel in REQUIRED:
        assert (REPO_ROOT / rel).exists(), f"Missing required hostile-case suite path: {rel}"
        assert rel in script, f"Mandatory security gate missing hostile-case suite wiring: {rel}"
