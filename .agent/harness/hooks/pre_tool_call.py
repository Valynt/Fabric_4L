"""Runs before every tool call. Enforces permissions and tool schemas."""
import json, os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _schema(tool_name):
    p = os.path.join(ROOT, "protocols/tool_schemas", f"{tool_name}.schema.json")
    if not os.path.exists(p):
        return {}
    return json.load(open(p))


def _perms_text():
    p = os.path.join(ROOT, "protocols/permissions.md")
    return open(p).read() if os.path.exists(p) else ""


def _blocked_target_reason(operation, op, args):
    blocked = op.get("blocked_targets", [])
    target = args.get("branch") or args.get("target") or args.get("env") or ""
    if target and target in blocked:
        return False, f"BLOCKED: {operation} to '{target}' is forbidden"
    return None


def _approval_reason(operation, op):
    if op.get("requires_approval", False):
        return "approval_needed", f"{operation} requires human approval"
    return None


def _never_allowed_lines(perms):
    if "## Never allowed" not in perms:
        return []
    return perms.split("## Never allowed")[1].split("##")[0].strip().splitlines()


def _permission_rule_matches(line, desc):
    if not line.startswith("- "):
        return False
    rule = line[2:].lower()
    keywords = [word for word in rule.split() if len(word) > 3]
    return bool(keywords and sum(1 for keyword in keywords if keyword in desc) >= 2)


def _permission_rule_reason(tool_name, operation, args):
    desc = f"{tool_name} {operation} {json.dumps(args)}".lower()
    for line in _never_allowed_lines(_perms_text()):
        if _permission_rule_matches(line, desc):
            return False, f"BLOCKED by permission rule: {line[2:]}"
    return None


def check_tool_call(tool_name, operation, args):
    """Returns (allowed, reason). allowed may be True, False, or 'approval_needed'."""
    op = _schema(tool_name).get("operations", {}).get(operation, {})
    for check in (
        _blocked_target_reason(operation, op, args),
        _approval_reason(operation, op),
        _permission_rule_reason(tool_name, operation, args),
    ):
        if check:
            return check

    return True, "allowed"
