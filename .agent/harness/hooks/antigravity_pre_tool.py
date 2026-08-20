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

APPROVED_EXTERNAL_DOMAINS = [
    "api.github.com",
    "registry.npmjs.org",
    "pypi.org",
    "api.anthropic.com",
    "api.openai.com",
]

FORBIDDEN_COMMAND_PATTERNS = [
    (r"git\s+(?:-[^\s]+\s+)*push\b.*(?:\s--force|\s-f|\s\+).*(?:main|production|staging|master)", "Force push to protected branches is forbidden."),
    (r"git\s+(?:-[^\s]+\s+)*push\b.*(?:main|production|staging|master).*(?:\s--force|\s-f|\s\+)", "Force push to protected branches is forbidden."),
    (r"rm\s+-rf\s+(?:/|/\*|c:\\|c:/\*)", "Destructive filesystem root deletion is forbidden."),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Fork bombs are forbidden."),
    (r"(?:cat|type|Get-Content)\s+.*(?:\.env|\.env\.local|\.infisical\.key)\b", "Direct raw credential access is forbidden; use injected environment variables."),
    (r"(?:^|[\s;|&])(?:echo|cat|type|printf|cp|copy|mv|move|rm|del|Remove-Item|Set-Content|Add-Content)\b.*permissions\.(?:md|json)\b", "Modifying permissions protocol file via shell is forbidden (only humans edit this file)."),
]

APPROVAL_COMMAND_PATTERNS = [
    (r"git\s+(?:-[^\s]+\s+)*push\b", "Pushing branches to remote repository requires approval."),
    (r"kubectl\s+delete\s+", "Kubernetes deletion operations require human approval."),
    (r"docker\s+system\s+prune", "Docker system prune requires human approval."),
    (r"(?:gh\s+pr\s+merge|git\s+merge\b)", "Merging pull requests requires human approval."),
    (r"(?:alembic|make\s+migrate|prisma\s+migrate)", "Running database migrations requires human approval."),
    (r"(?:pip\s+install|npm\s+install|pnpm\s+(?:add|install|update)|uv\s+(?:pip\s+install|add))\b", "Installing new dependencies or upgrading versions requires human approval."),
    (r"(?:rm\s+|del\s+|Remove-Item\s+)(?!.*memory[/\\]working)", "Deleting files outside of memory/working/ requires approval."),
]


def evaluate_decision(payload):
    if not isinstance(payload, dict) or "toolCall" not in payload:
        return {"decision": "deny", "reason": "PreTool hook error: payload must contain a toolCall object"}

    tool_call = payload["toolCall"]
    if not isinstance(tool_call, dict):
        return {"decision": "deny", "reason": "PreTool hook error: toolCall must be an object"}

    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}
    if not isinstance(args, dict):
        args = {}

    # 1. Shell command checks
    if tool_name in ("run_command", "bash", "execute_command"):
        cmd = args.get("CommandLine") or args.get("command") or ""

        # Check hard forbidden patterns
        for pattern, reason in FORBIDDEN_COMMAND_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return {"decision": "deny", "reason": reason}

        # Check external domain calls in commands (e.g. curl / wget / Invoke-WebRequest)
        url_match = re.search(r"(?:https?://)([^/\s\'\"\`]+)", cmd)
        if url_match:
            domain = url_match.group(1).lower()
            if not any(domain == approved or domain.endswith("." + approved) for approved in APPROVED_EXTERNAL_DOMAINS):
                return {"decision": "deny", "reason": f"HTTP requests to domain '{domain}' not in approved list."}

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
        # Modifying CI/CD workflows requires approval
        if ".github/workflows" in target_file.replace("\\", "/"):
            return {"decision": "ask", "reason": "Modifying CI/CD configuration requires approval."}

    # 3. HTTP / Network tool checks if present
    if tool_name in ("http_request", "fetch_url", "web_fetch"):
        url = args.get("url") or ""
        url_match = re.search(r"(?:https?://)([^/\s\'\"\`]+)", url)
        if url_match:
            domain = url_match.group(1).lower()
            if not any(domain == approved or domain.endswith("." + approved) for approved in APPROVED_EXTERNAL_DOMAINS):
                return {"decision": "deny", "reason": f"HTTP requests to domain '{domain}' not in approved list."}

    return {"decision": "allow"}


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            result = {"decision": "deny", "reason": "PreTool hook error: payload must be a JSON object"}
        else:
            result = evaluate_decision(payload)
    except Exception as e:
        # A security guard must fail closed when it cannot evaluate the request.
        result = {"decision": "deny", "reason": f"PreTool hook error: {e}"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
