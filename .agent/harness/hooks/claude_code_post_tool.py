#!/usr/bin/env python3
"""Smart PostToolUse hook for Claude Code.

Claude Code calls this script after every matched tool use and passes a
JSON payload via stdin:

    {
      "session_id": "...",
      "tool_name": "Bash",
      "tool_input": {"command": "supabase db push"},
      "tool_response": {"output": "...", "exit_code": 0, "error": ""}
    }

The old hook called memory_reflect.py with hardcoded "post-tool ok" —
every entry looked identical so content_cluster() found nothing and the
dream cycle produced zero candidates. This version:

  - reads tool_name / tool_input / tool_response from stdin
  - falls back to CLAUDE_TOOL_NAME / CLAUDE_TOOL_INPUT env vars
  - detects failures from exit codes, error fields, and stderr content
  - scores importance by domain (deploy/migrate/schema = 8, edit = 5, etc.)
  - generates a non-empty reflection the dream cycle can actually cluster on
  - calls the same log_execution / on_failure path as the rest of the harness

Drop-in for the old command in settings.json:
    "command": "python3 .agent/harness/hooks/claude_code_post_tool.py"
"""
import json, os, re, sys

# Resolve .agent/ root from this file's location:
#   __file__  = .agent/harness/hooks/claude_code_post_tool.py
#   UP 1      = .agent/harness/hooks/
#   UP 2      = .agent/harness/
#   UP 3      = .agent/
HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

sys.path.insert(0, os.path.join(AGENT_ROOT, "harness"))
sys.path.insert(0, os.path.join(AGENT_ROOT, "tools"))

from hooks.post_execution import log_execution   # noqa: E402
from hooks.on_failure import on_failure          # noqa: E402


# ---------------------------------------------------------------------------
# Importance scoring
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Importance patterns — universal core + user-configurable extras
# ---------------------------------------------------------------------------

# Patterns that are high-stakes on ANY stack.
# Rule of thumb: if getting it wrong on a project you've never seen before
# would cause data loss, a production outage, or a security incident, it
# belongs here. Service names (supabase, stripe, vercel…) do NOT belong
# here — put those in .agent/protocols/hook_patterns.json.
_UNIVERSAL_HIGH = [
    r'deploy|deployment|release|rollback',
    r'migration|migrate',
    r'schema|alter\s+table|drop\s+table|create\s+table|truncate',
    r'production|prod\b|staging\b',
    r'force.?push|push\s+--force',
    r'secret|credential',
]

# Patterns that matter but are recoverable on any stack.
_UNIVERSAL_MEDIUM = [
    r'commit|push|merge|rebase',
    r'test|spec|build|bundle|compile',
    r'install|upgrade|uninstall',
    r'delete|remove|unlink',
    r'chmod|chown|cron|systemctl',
]


def _load_user_patterns() -> tuple[list[str], list[str]]:
    """Read extra high/medium patterns from .agent/protocols/hook_patterns.json.

    Returns (high_extras, medium_extras) — lists of raw regex fragments.
    Missing file or bad JSON is silently ignored so the hook never fails
    because a config file is absent or malformed.

    The config file lives at .agent/protocols/hook_patterns.json and is
    owned entirely by the user. Add your own service names, CLI tools, and
    domain terms there — not in this file.
    """
    config_path = os.path.join(AGENT_ROOT, "protocols", "hook_patterns.json")
    if not os.path.isfile(config_path):
        return [], []
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], []
    raw_high   = [str(p) for p in cfg.get("high_stakes",   []) if p]
    raw_medium = [str(p) for p in cfg.get("medium_stakes", []) if p]
    # Drop fragments that aren't valid standalone regex — a single typo
    # (e.g. unbalanced paren) would otherwise kill every PostToolUse
    # invocation until the config file is hand-fixed.
    return _filter_valid(raw_high), _filter_valid(raw_medium)


def _filter_valid(fragments: list[str]) -> list[str]:
    good = []
    for frag in fragments:
        try:
            re.compile(frag)
        except re.error as e:
            import sys
            print(
                f"hook_patterns.json: skipping invalid regex {frag!r}: {e}",
                file=sys.stderr,
            )
            continue
        good.append(frag)
    return good


def _build_pattern(fragments: list[str]) -> re.Pattern | None:
    """Compile fragments into a combined word-boundary pattern.
    Returns None on failure; caller decides on fallback behavior."""
    if not fragments:
        return None
    combined = r'\b(' + '|'.join(fragments) + r')\b'
    try:
        return re.compile(combined, re.IGNORECASE)
    except re.error:
        return None


def _build_with_fallback(universals: list[str],
                         user: list[str]) -> re.Pattern | None:
    """Try merging universal + user fragments. If the merged pattern fails
    to compile (one fragment like `(?i)foo` that is valid standalone, OR
    two fragments that only conflict together like duplicate named groups),
    rebuild INCREMENTALLY: add each user fragment only if it still compiles
    with everything we've kept so far. This way one bad entry doesn't
    disable every custom rule, and inter-fragment conflicts are resolved
    first-wins (deterministic)."""
    merged = _build_pattern(universals + user)
    if merged is not None or not user:
        return merged
    import sys
    surviving: list[str] = []
    for frag in user:
        if _build_pattern(universals + surviving + [frag]) is not None:
            surviving.append(frag)
        else:
            print(
                f"hook_patterns.json: fragment {frag!r} is incompatible "
                "with the rest of the pattern; dropping it.",
                file=sys.stderr,
            )
    return _build_pattern(universals + surviving)


# Build once at import time.  User patterns are merged in here so there's
# no per-call file I/O.
_user_high, _user_medium = _load_user_patterns()
_HIGH   = _build_with_fallback(_UNIVERSAL_HIGH,   _user_high)
_MEDIUM = _build_with_fallback(_UNIVERSAL_MEDIUM, _user_medium)


def _importance(tool_name: str, tool_input_str: str) -> int:
    if _HIGH and _HIGH.search(tool_input_str):
        return 9
    if tool_name in ("Edit", "MultiEdit", "Write"):
        if _MEDIUM and _MEDIUM.search(tool_input_str):
            return 6
        return 5
    if _MEDIUM and _MEDIUM.search(tool_input_str):
        return 6
    return 3


def _pain_score(importance: int, success: bool) -> int:
    """Pain score calibrated so high-importance recurring successes cross
    the dream-cycle promotion threshold (7.0).

    For a cluster of 3 high-importance successes:
      salience = recency(10) × pain(0.5) × importance(0.9) × recurrence(3) = 13.5
      → comfortably clears 7.0.

    Routine successes (importance ≤ 6) stay at pain=2 so they don't flood
    the candidate queue.
    """
    if not success:
        return 8 if importance < 9 else 10
    if importance >= 8:
        return 5  # significant success — recurring pattern should promote
    if importance >= 6:
        return 3
    return 2


# ---------------------------------------------------------------------------
# Failure detection
# ---------------------------------------------------------------------------

_ERROR_SIGNALS = re.compile(
    r'\b(error|exception|traceback|failed|failure|'
    r'denied|forbidden|unauthorized|'
    r'ENOENT|EACCES|EPERM|ECONNREFUSED|'
    r'cannot|could not|unable to|not found)\b',
    re.IGNORECASE,
)

# Patterns where the user has explicitly asked the shell to mask a non-zero
# exit PER-COMMAND. When a command uses these, exit_code=0 is NOT reliable,
# so we fall through to the generic stdout heuristic.
# Examples: `deploy || true`, `migrate || :`, `run; true`.
# Deliberately NOT matching `set +e`: it's often a temporary disable around
# `grep Error logfile; rc=$?; set -e`-style patterns where exit_code=0 IS
# still trustworthy for the actual command.
_EXIT_MASKED = re.compile(
    r'\|\|\s*(?:true|:|exit\s+0)'    # || true   ||  :   || exit 0
    r'|;\s*(?:true|:)\s*$',          # ; true    ; :  at end of command
    re.IGNORECASE,
)


_QUOTED_STRING = re.compile(
    r"'[^']*'"                      # single-quoted (no escapes in bash)
    r'|"(?:[^"\\]|\\.)*"',          # double-quoted, honoring backslash escapes
)


def _is_exit_masked(command: str) -> bool:
    """Return True if the Bash command explicitly suppresses its exit code.
    Strips single/double-quoted regions before matching so that masked-exit
    tokens inside quoted strings (e.g. `echo '... || true ...'`) don't
    produce false positives. Heredocs are not parsed; that corner case
    (text between <<EOF ... EOF lines containing || true) can still slip
    through, but is rare enough in real Bash tool use to accept."""
    if not command:
        return False
    stripped = _QUOTED_STRING.sub("", command)
    return bool(_EXIT_MASKED.search(stripped))


def _extract_bash_command(tool_input: dict) -> str:
    """Pull the Bash command string from tool_input, supporting both the
    modern `{"command": "..."}` shape and the env-var fallback `{"raw": "..."}`
    shape that `main()` constructs from `CLAUDE_TOOL_INPUT`."""
    if not isinstance(tool_input, dict):
        return ""
    cmd = tool_input.get("command")
    if isinstance(cmd, str) and cmd:
        return cmd
    raw = tool_input.get("raw")
    if isinstance(raw, str) and raw:
        return raw
    return ""


def _is_success(tool_name: str, tool_input_or_resp, resp=None) -> bool:
    """Signature:
        _is_success(tool_name, tool_input, resp)   — preferred, 3-arg form
        _is_success(tool_name, resp)               — legacy 2-arg form;
            wrapper detection off
    Detects failure from the tool_response dict. Conservative — only fails
    on unambiguous signals so we don't discard genuine successes."""
    if resp is None:
        tool_input: dict = {}
        resp = tool_input_or_resp
    else:
        tool_input = tool_input_or_resp if isinstance(tool_input_or_resp, dict) else {}
    return _is_success_impl(tool_name, tool_input, resp)


def _stderr_text(resp: dict) -> str:
    return resp.get("error", "") or resp.get("stderr", "") or ""


def _stderr_indicates_failure(stderr: str, wrapped: bool) -> bool:
    if not stderr:
        return False
    if wrapped:
        return bool(_ERROR_SIGNALS.search(stderr))
    return len(stderr) > 30 and bool(_ERROR_SIGNALS.search(stderr))


def _exit_code_success(resp: dict):
    exit_code = resp.get("exit_code")
    if exit_code is None:
        return None
    return exit_code == 0


def _bash_success(tool_input: dict, resp: dict):
    if resp.get("interrupted", False):
        return False
    command = _extract_bash_command(tool_input)
    wrapped = _is_exit_masked(command)
    if _stderr_indicates_failure(_stderr_text(resp), wrapped):
        return False
    return _exit_code_success(resp)


def _first_output_line(output: str) -> str:
    return output.strip().splitlines()[0] if output.strip() else ""


def _generic_output_success(resp: dict):
    output = _extract_output(resp)
    if not output or not _ERROR_SIGNALS.search(output[:200]):
        return True
    return not bool(_ERROR_SIGNALS.search(_first_output_line(output)))


def _is_success_impl(tool_name: str, tool_input: dict, resp: dict) -> bool:
    """Detect failure from the tool_response dict. Conservative — only fails
    on unambiguous signals so we don't discard genuine successes."""
    if not isinstance(resp, dict):
        return True
    if resp.get("is_error", False):
        return False
    if tool_name == "Bash":
        bash_result = _bash_success(tool_input, resp)
        if bash_result is not None:
            return bash_result
    return _generic_output_success(resp)


# ---------------------------------------------------------------------------
# Output extraction (handles multiple Claude Code response shapes)
# ---------------------------------------------------------------------------

def _extract_output(resp: dict) -> str:
    """Pull plain text from whatever shape tool_response comes in."""
    if not isinstance(resp, dict):
        return str(resp)[:300]

    # Shape 1: direct string fields
    for key in ("output", "stdout", "result", "text"):
        if isinstance(resp.get(key), str):
            return resp[key][:500]

    # Shape 2: content array (newer Claude Code versions)
    content = resp.get("content")
    if isinstance(content, list):
        texts = [
            c.get("text", "") for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]
        return " ".join(texts)[:500]

    # Shape 3: raw string response
    if isinstance(resp, str):
        return resp[:500]

    return ""


def _extract_error(resp: dict) -> str:
    if not isinstance(resp, dict):
        return ""
    for key in ("error", "stderr", "error_message"):
        v = resp.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()[:300]
    return ""


# ---------------------------------------------------------------------------
# Action label (short, searchable)
# ---------------------------------------------------------------------------

def _path_value(tool_input: dict, *keys) -> str:
    for key in keys:
        value = tool_input.get(key)
        if value:
            return value
    return "?"


def _bash_label(tool_input: dict) -> str:
    cmd = tool_input.get("command", "").strip()
    first = re.sub(r"\s+", " ", cmd.split("\n")[0].split(";")[0])[:80]
    return f"bash: {first}"


def _edit_label(tool_input: dict) -> str:
    return f"edit: {_path_value(tool_input, 'file_path', 'path', 'new_path')}"


def _write_label(tool_input: dict) -> str:
    return f"write: {_path_value(tool_input, 'file_path', 'path')}"


def _read_label(tool_input: dict) -> str:
    return f"read: {_path_value(tool_input, 'file_path', 'path')}"


def _todo_label(tool_input: dict) -> str:
    pending = [
        todo for todo in tool_input.get("todos", [])
        if isinstance(todo, dict) and todo.get("status") == "in_progress"
    ]
    if pending:
        return f"todo-update: {pending[0].get('content', '')[:60]}"
    return "todo: updated task list"


def _task_label(tool_input: dict) -> str:
    return f"task: {(tool_input.get('description') or '')[:60]}"


def _webfetch_label(tool_input: dict) -> str:
    return f"fetch: {(tool_input.get('url') or '')[:60]}"


_ACTION_LABELS = {
    "Bash": _bash_label,
    "Edit": _edit_label,
    "MultiEdit": _edit_label,
    "Write": _write_label,
    "Read": _read_label,
    "TodoWrite": _todo_label,
    "Task": _task_label,
    "WebFetch": _webfetch_label,
}


def _action_label(tool_name: str, tool_input: dict) -> str:
    """First-word summary. Ends up in the `action` field of the episodic entry."""
    labeler = _ACTION_LABELS.get(tool_name)
    if labeler:
        return labeler(tool_input)
    return f"tool:{tool_name}"


# ---------------------------------------------------------------------------
# Reflection generation (this is what the dream cycle clusters on)
# ---------------------------------------------------------------------------

def _short_command(tool_input: dict) -> tuple[str, str]:
    cmd = tool_input.get("command", "").strip()
    return cmd, re.sub(r"\s+", " ", cmd.split("\n")[0])[:100]


def _append_error(parts: list[str], tool_response: dict) -> None:
    err = _extract_error(tool_response)
    if err:
        parts.append(f"Error: {err[:120]}")


def _bash_reflection(tool_input: dict, tool_response: dict, success: bool) -> list[str]:
    cmd, short_cmd = _short_command(tool_input)
    match = _HIGH.search(cmd)
    if match:
        domain = match.group(0).lower().replace(" ", "-")
        status = "completed" if success else "FAILED"
        parts = [f"High-stakes op {status} ({domain}): {short_cmd}"]
        if not success:
            _append_error(parts, tool_response)
        return parts
    if success:
        return [f"Ran: {short_cmd}"]
    parts = [f"Command failed: {short_cmd}"]
    _append_error(parts, tool_response)
    return parts


def _edit_reflection(tool_input: dict, _tool_response: dict, success: bool) -> list[str]:
    path = tool_input.get("file_path") or tool_input.get("path") or "?"
    old = (tool_input.get("old_string") or "")[:50]
    new = (tool_input.get("new_string") or "")[:50]
    if old and new:
        parts = [
            f"Edited {path}: replaced {repr(old[:30])} "
            f"with {repr(new[:30])}"
        ]
    else:
        parts = [f"Edited {path}"]
    if not success:
        parts.append("Edit failed")
    return parts


def _write_reflection(tool_input: dict, _tool_response: dict, success: bool) -> list[str]:
    path = tool_input.get("file_path") or tool_input.get("path") or "?"
    content = tool_input.get("content") or ""
    lines = content.count("\n") + 1 if content else 0
    parts = [f"Wrote {path} ({lines} lines)"]
    if not success:
        parts.append("Write failed")
    return parts


def _todo_reflection(tool_input: dict, _tool_response: dict, _success: bool) -> list[str]:
    todos = tool_input.get("todos", [])
    done = [
        todo for todo in todos
        if isinstance(todo, dict) and todo.get("status") == "completed"
    ]
    in_progress = [
        todo for todo in todos
        if isinstance(todo, dict) and todo.get("status") == "in_progress"
    ]
    parts = []
    if done:
        parts.append(f"Completed todo: {done[-1].get('content','')[:60]}")
    if in_progress:
        parts.append(f"Now working on: {in_progress[0].get('content','')[:60]}")
    return parts or [f"Updated todo list ({len(todos)} items)"]


def _fallback_reflection(tool_name: str, tool_input: dict, success: bool) -> list[str]:
    status = "successfully" if success else "with failure"
    parts = [f"Tool {tool_name} completed {status}"]
    inp_str = json.dumps(tool_input)
    if inp_str and len(inp_str) < 80:
        parts.append(inp_str)
    return parts


_REFLECTIONS = {
    "Bash": _bash_reflection,
    "Edit": _edit_reflection,
    "MultiEdit": _edit_reflection,
    "Write": _write_reflection,
    "TodoWrite": _todo_reflection,
}


def _reflection(tool_name: str, tool_input: dict,
                tool_response: dict, success: bool) -> str:
    """
    Produce a non-empty, content-rich reflection string. This is the most
    important field for the dream cycle — content_cluster() calls word_set()
    on it. An empty reflection means zero clustering signal.
    """
    builder = _REFLECTIONS.get(tool_name)
    if builder:
        parts = builder(tool_input, tool_response, success)
    else:
        parts = _fallback_reflection(tool_name, tool_input, success)
    return ". ".join(parts) if parts else f"Tool {tool_name} ran"


# ---------------------------------------------------------------------------
# Detail field — what went in / what came out
# ---------------------------------------------------------------------------

def _detail(tool_name: str, tool_input: dict,
            tool_response: dict, success: bool) -> str:
    """
    Stored in `detail`. More verbose than reflection. Truncated to 500 chars
    by log_execution anyway.
    """
    output = _extract_output(tool_response)
    inp_str = json.dumps(tool_input, separators=(",", ":"))[:300]

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")[:120]
        if not success:
            err = _extract_error(tool_response)
            return f"cmd={cmd!r} | exit≠0 | err={err[:200]}"
        out_snip = output[:200] if output else ""
        return f"cmd={cmd!r}" + (f" | out={out_snip}" if out_snip else "")

    return inp_str + (f" | {output[:150]}" if output else "")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _read_payload() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _json_or_raw(value):
    if not isinstance(value, str):
        return value or {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return {"raw": value}


def _payload_field(payload: dict, key: str, env_key: str):
    value = _json_or_raw(payload.get(key) or {})
    if value:
        return value
    return _json_or_raw(os.environ.get(env_key, ""))


def _normalize_payload(payload: dict) -> tuple[str, dict, dict]:
    tool_name = payload.get("tool_name") or os.environ.get("CLAUDE_TOOL_NAME") or "Unknown"
    tool_input = _payload_field(payload, "tool_input", "CLAUDE_TOOL_INPUT")
    tool_response = _payload_field(payload, "tool_response", "CLAUDE_TOOL_RESPONSE")
    return tool_name, tool_input, tool_response


def _emit_memory_entry(tool_name: str, tool_input: dict, tool_response: dict) -> None:
    tool_input = tool_input if isinstance(tool_input, dict) else {"raw": str(tool_input)}
    tool_response = tool_response if isinstance(tool_response, dict) else {"raw": str(tool_response)}

    success = _is_success(tool_name, tool_input, tool_response)
    importance = _importance(tool_name, json.dumps(tool_input))
    action = _action_label(tool_name, tool_input)
    reflection = _reflection(tool_name, tool_input, tool_response, success)
    detail = _detail(tool_name, tool_input, tool_response, success)
    pscore = _pain_score(importance, success)
    if success:
        log_execution(
            skill_name="claude-code",
            action=action,
            result=detail,
            success=True,
            reflection=reflection,
            importance=importance,
            confidence=0.7,
            pain_score=pscore,
        )
    else:
        on_failure(
            skill_name="claude-code",
            action=action,
            error=reflection,
            context=detail,
            confidence=0.7,
            importance=importance,
            pain_score=pscore,
        )


def main() -> None:
    tool_name, tool_input, tool_response = _normalize_payload(_read_payload())
    _emit_memory_entry(tool_name, tool_input, tool_response)


if __name__ == "__main__":
    main()
