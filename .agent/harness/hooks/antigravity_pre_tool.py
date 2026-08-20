#!/usr/bin/env python3
"""Antigravity PreToolUse Lifecycle Hook.

Enforces security, tenant isolation, and permission boundaries before tool execution.
Receives Antigravity hook payload on stdin:
    {
      "toolCall": {"name": "run_command", "args": {"CommandLine": "..."}},
      "stepIdx": 1,
      "conversationId": "...",
      "workspacePaths": [...]
    }
Outputs decision JSON:
    {"decision": "allow" | "deny" | "ask", "reason": "..."}
"""
import json, os, re, sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(AGENT_ROOT, "harness"))
sys.path.insert(0, os.path.join(AGENT_ROOT, "tools"))

FORBIDDEN_COMMAND_PATTERNS = [
    (r"git\s+push\b.*(?:\s--force|\s-f|\s\+).*(?:main|production|staging|master)", "Force push to protected branches is forbidden."),
    (r"git\s+push\b.*(?:main|production|staging|master).*(?:\s--force|\s-f|\s\+)", "Force push to protected branches is forbidden."),
    (r"rm\s+-rf\s+(?:/|/\*|c:\\|c:/\*)", "Destructive filesystem root deletion is forbidden."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Fork bombs are forbidden."),
    (r"(?:cat|type|Get-Content)\s+.*(?:\.env|\.env\.local|\.infisical\.key)\b", "Direct raw credential access is forbidden; use injected environment variables."),
]

APPROVAL_COMMAND_PATTERNS = [
    (r"git\s+push\s+", "Pushing branches to remote repository requires approval."),
    (r"kubectl\s+delete\s+", "Kubernetes deletion operations require human approval."),
    (r"docker\s+system\s+prune", "Docker system prune requires human approval."),
]


def evaluate_decision(payload):
    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}

    # 1. Shell command checks
    if tool_name in ("run_command", "bash", "execute_command"):
        cmd = args.get("CommandLine") or args.get("command") or ""

        # Check hard forbidden patterns
        for pattern, reason in FORBIDDEN_COMMAND_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return {"decision": "deny", "reason": reason}

        # Check approval patterns
        for pattern, reason in APPROVAL_COMMAND_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return {"decision": "ask", "reason": reason}

    # 2. File write checks
    if tool_name in ("write_to_file", "replace_file_content", "multi_replace_file_content"):
        target_file = args.get("TargetFile") or args.get("path") or ""
        # Protect permissions.md from automated tampering
        if target_file.endswith("permissions.md") or target_file.endswith("permissions.json"):
            return {"decision": "deny", "reason": "Permissions protocol file can only be modified by humans."}

    return {"decision": "allow"}


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        result = evaluate_decision(payload)
    except Exception as e:
        # A security guard must fail closed when it cannot evaluate the request.
        result = {"decision": "deny", "reason": f"PreTool hook error: {e}"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
