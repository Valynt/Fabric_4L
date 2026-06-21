"""Regression coverage for .agent support-code complexity refactors."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / ".agent" / "harness"
HOOKS = HARNESS / "hooks"
MEMORY = ROOT / ".agent" / "memory"

for path in (HARNESS, HOOKS, MEMORY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def test_context_budget_filters_and_ranks_terminal_lessons():
    context_budget = importlib.import_module("context_budget")
    lessons_md = """
- Alpha billing workflow lesson  <!-- status=accepted confidence=0.9 evidence=1 id=a -->
- [PROVISIONAL] Alpha draft lesson  <!-- status=provisional confidence=0.2 evidence=1 id=b -->
- ~~Alpha superseded lesson~~  <!-- status=accepted confidence=0.8 evidence=1 id=c superseded_by=d -->
- Zeta graph retrieval lesson  <!-- status=accepted confidence=0.8 evidence=1 id=e -->
"""

    ranked = context_budget._top_lessons("graph retrieval", lessons_md)

    assert "Zeta graph retrieval lesson" in ranked.splitlines()[0]
    assert "Alpha billing workflow lesson" not in ranked
    assert "Alpha draft lesson" not in ranked
    assert "Alpha superseded lesson" not in ranked


def test_claude_hook_classifies_bash_success_failure_and_reflections():
    cc = importlib.import_module("hooks.claude_code_post_tool")

    assert cc._is_success("Bash", {"command": "pytest"}, {"exit_code": 0})
    assert not cc._is_success("Bash", {"command": "pytest"}, {"exit_code": 1})
    assert not cc._is_success("Bash", {"command": "build || true"}, {
        "exit_code": 0,
        "stderr": "build failed",
    })
    assert not cc._is_success("Bash", {"command": "pytest"}, {"interrupted": True})
    assert not cc._is_success("Read", {}, {"output": "Error: file missing"})

    action = cc._action_label("Edit", {"file_path": "apps/web/src/App.tsx"})
    reflection = cc._reflection(
        "Bash",
        {"command": "deploy production"},
        {"error": "permission denied"},
        False,
    )
    detail = cc._detail("Bash", {"command": "pytest"}, {"output": "ok"}, True)

    assert action == "edit: apps/web/src/App.tsx"
    assert reflection.startswith("High-stakes op FAILED (deploy): deploy production")
    assert "Error: permission denied" in reflection
    assert detail == "cmd='pytest' | out=ok"


def test_pi_hook_normalizes_response_and_malformed_payload(monkeypatch):
    pi = importlib.import_module("hooks.pi_post_tool")
    calls = []
    monkeypatch.setattr(pi, "on_failure", lambda **kwargs: calls.append(kwargs))

    response = pi._normalize_response({
        "isError": True,
        "details": {"stdout": "done", "stderr": "bad", "exitCode": 2},
        "content": [{"type": "text", "text": "content output"}],
    })

    assert response["is_error"] is True
    assert response["stdout"] == "done"
    assert response["stderr"] == "bad"
    assert response["exit_code"] == 2
    assert response["output"] == "content output"

    pi._emit_malformed("missing tool_name", "{bad")
    assert calls[0]["skill_name"] == "pi"
    assert calls[0]["action"] == "hook:malformed_payload"
    assert calls[0]["importance"] == 5


def test_pre_tool_call_blocks_approval_and_permission_rules(monkeypatch):
    pre = importlib.import_module("hooks.pre_tool_call")
    monkeypatch.setattr(pre, "_schema", lambda _tool: {
        "operations": {
            "deploy": {
                "blocked_targets": ["production"],
                "requires_approval": False,
            },
            "migrate": {"requires_approval": True},
        }
    })

    assert pre.check_tool_call("git", "deploy", {"target": "production"}) == (
        False,
        "BLOCKED: deploy to 'production' is forbidden",
    )
    assert pre.check_tool_call("git", "migrate", {}) == (
        "approval_needed",
        "migrate requires human approval",
    )

    monkeypatch.setattr(pre, "_schema", lambda _tool: {"operations": {}})
    monkeypatch.setattr(
        pre,
        "_perms_text",
        lambda: "## Never allowed\n- delete production database\n## Allowed\n",
    )
    allowed, reason = pre.check_tool_call("db", "delete", {"target": "production database"})
    assert allowed is False
    assert reason == "BLOCKED by permission rule: delete production database"


def test_render_lessons_migrates_legacy_and_renders_supersession(tmp_path):
    render_lessons = importlib.import_module("render_lessons")
    semantic_dir = tmp_path / "semantic"
    semantic_dir.mkdir()
    lessons_md = semantic_dir / render_lessons.LESSONS_MD
    lessons_md.write_text(
        "# Lessons\n\n"
        f"{render_lessons.SENTINEL}\n\n"
        "- Keep this migrated lesson\n"
        "- [PROVISIONAL] Strip provisional marker\n"
        "- ~~Skip superseded migrated lesson~~\n",
        encoding="utf-8",
    )

    assert render_lessons.migrate_legacy_bullets(str(semantic_dir)) == 2
    assert render_lessons.migrate_legacy_bullets(str(semantic_dir)) == 0

    render_lessons.append_lesson({
        "id": "old",
        "claim": "Use the old guidance",
        "status": "accepted",
        "accepted_at": "2026-06-01T00:00:00+00:00",
        "confidence": 0.8,
        "evidence_ids": ["e1"],
    }, str(semantic_dir))
    render_lessons.append_lesson({
        "id": "new",
        "claim": "Use the new guidance",
        "status": "accepted",
        "accepted_at": "2026-06-02T00:00:00+00:00",
        "confidence": 0.9,
        "evidence_ids": ["e2"],
        "supersedes": "old",
    }, str(semantic_dir))

    rendered = Path(render_lessons.render_lessons(str(semantic_dir))).read_text(encoding="utf-8")
    assert "Keep this migrated lesson" in rendered
    assert "Strip provisional marker" in rendered
    assert "Skip superseded migrated lesson" not in rendered
    assert "~~Use the old guidance~~" in rendered
    assert "Use the new guidance" in rendered


def test_promote_write_candidates_preserves_lifecycle_and_skips_duplicates(tmp_path):
    promote = importlib.import_module("promote")
    candidates_dir = tmp_path / "candidates"
    rejected_dir = candidates_dir / "rejected"
    semantic_dir = tmp_path / "semantic"
    rejected_dir.mkdir(parents=True)
    semantic_dir.mkdir()
    (semantic_dir / "LESSONS.md").write_text(
        "- Already accepted claim  <!-- status=accepted confidence=0.9 evidence=1 id=a -->\n",
        encoding="utf-8",
    )

    rejected = {
        "id": "recur",
        "status": "rejected",
        "staged_at": "2026-01-01T00:00:00+00:00",
        "rejection_count": 2,
        "decisions": [{
            "action": "rejected",
            "evidence_snapshot": ["old"],
            "duplicate_claims": ["Missing blocker"],
        }],
    }
    (rejected_dir / "recur.json").write_text(json.dumps(rejected), encoding="utf-8")

    written = promote.write_candidates({
        "dup": {
            "id": "dup",
            "name": "dup",
            "claim": "Already accepted claim",
            "evidence_ids": ["e1"],
        },
        "recur": {
            "id": "recur",
            "name": "recur",
            "claim": "A recurring useful claim",
            "evidence_ids": ["old"],
            "cluster_size": 3,
        },
    }, str(candidates_dir))

    assert written == 1
    assert not (rejected_dir / "recur.json").exists()
    candidate = json.loads((candidates_dir / "recur.json").read_text(encoding="utf-8"))
    assert candidate["staged_at"] == "2026-01-01T00:00:00+00:00"
    assert candidate["rejection_count"] == 2
    assert [d["action"] for d in candidate["decisions"]] == ["rejected", "staged"]
    assert not (candidates_dir / "dup.json").exists()
