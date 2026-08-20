"""Regression tests for the Antigravity pre-tool security hook."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


HOOK = (
    Path(__file__).resolve().parents[2]
    / ".agent"
    / "harness"
    / "hooks"
    / "antigravity_pre_tool.py"
)


def _run_hook(payload: str) -> dict[str, str]:
    process = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(process.stdout)


def test_pre_tool_hook_denies_malformed_json() -> None:
    result = _run_hook("{")

    assert result["decision"] == "deny"
    assert "error" in result["reason"].lower()


def test_pre_tool_hook_denies_payload_with_invalid_tool_call_shape() -> None:
    result = _run_hook(json.dumps({"toolCall": "not-an-object"}))

    assert result["decision"] == "deny"
    assert "error" in result["reason"].lower()
