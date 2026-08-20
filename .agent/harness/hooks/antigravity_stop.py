#!/usr/bin/env python3
"""Antigravity Stop Lifecycle Hook.

Executes when an agent turn/session loop ends.
Receives payload on stdin:
    {
      "executionNum": 1,
      "terminationReason": "model_stop",
      "fullyIdle": true,
      "conversationId": "..."
    }
Runs the memory auto-dream cycle to distill recent episodes into review candidates.
Outputs `{}` or `{"decision": "stop"}`.
"""
import json, os, subprocess, sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AUTO_DREAM = os.path.join(AGENT_ROOT, "memory", "auto_dream.py")


def main():
    try:
        raw = sys.stdin.read()
        if raw.strip():
            _ = json.loads(raw)
        
        # Run auto_dream in background if it exists
        if os.path.exists(AUTO_DREAM):
            python_exe = sys.executable or "python3"
            subprocess.run(
                [python_exe, AUTO_DREAM],
                cwd=AGENT_ROOT,
                capture_output=True,
                timeout=30,
            )
    except Exception:
        # Silently ignore background dream run errors on stop hook exit
        pass

    print(json.dumps({"decision": "stop"}))


if __name__ == "__main__":
    main()
