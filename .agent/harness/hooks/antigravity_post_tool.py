#!/usr/bin/env python3
"""Antigravity PostToolUse Lifecycle Hook.

Executes after tool runs in Antigravity.
Receives payload on stdin:
    {
      "stepIdx": 5,
      "error": "exit status 1",  // present if failed
      "conversationId": "...",
      "workspacePaths": [...]
    }
Logs execution to episodic memory (AGENT_LEARNINGS.jsonl) and triggers failure handler if failed.
Outputs empty JSON object `{}`.
"""
import json, os, sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(AGENT_ROOT, "harness"))
sys.path.insert(0, os.path.join(AGENT_ROOT, "tools"))

from hooks.post_execution import log_execution  # noqa: E402
from hooks.on_failure import on_failure  # noqa: E402


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        step_idx = payload.get("stepIdx", 0)
        error = payload.get("error") or ""
        conv_id = payload.get("conversationId") or "unknown"

        if error:
            on_failure(
                skill_name="antigravity-harness",
                action=f"step_{step_idx}_tool_call",
                error=error,
                context=f"conversation: {conv_id}",
                confidence=0.8,
                importance=7,
            )
        else:
            log_execution(
                skill_name="antigravity-harness",
                action=f"step_{step_idx}_tool_call",
                result="ok",
                success=True,
                reflection=f"step {step_idx} executed cleanly",
                importance=4,
            )
    except Exception:
        # Silently ignore memory logging errors to avoid blocking the tool lifecycle
        pass

    # Antigravity PostToolUse expects `{}` on stdout
    print("{}")


if __name__ == "__main__":
    main()
