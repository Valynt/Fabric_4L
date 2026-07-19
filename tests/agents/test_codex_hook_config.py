"""Regression tests for repository-local Codex lifecycle hooks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK_CONFIG = ROOT / ".codex" / "hooks.json"
GIT_ROOT_EXPRESSION = "$(git rev-parse --show-toplevel)"


def _commands() -> list[str]:
    config = json.loads(HOOK_CONFIG.read_text(encoding="utf-8"))
    return [
        hook["command"]
        for event in config["hooks"].values()
        for group in event
        for hook in group["hooks"]
        if hook["type"] == "command"
    ]


def test_codex_hooks_resolve_repository_scripts_from_git_root() -> None:
    commands = _commands()

    assert len(commands) == 2
    assert all("CLAUDE_PROJECT_DIR" not in command for command in commands)
    assert all(GIT_ROOT_EXPRESSION in command for command in commands)
    assert any("/.agent/harness/hooks/claude_code_post_tool.py" in command for command in commands)
    assert any("/.agent/memory/auto_dream.py" in command for command in commands)


def test_codex_hook_targets_exist() -> None:
    assert (ROOT / ".agent" / "harness" / "hooks" / "claude_code_post_tool.py").is_file()
    assert (ROOT / ".agent" / "memory" / "auto_dream.py").is_file()
