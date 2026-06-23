"""Layer 4 model-registry contract drift guards.

These tests are intentionally lightweight and source-based so they can run in CI
without requiring database fixtures.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_SERVICE = REPO_ROOT / "services/layer4-agents/src/layer4_agents/registry/service.py"
REGISTRY_ROUTES = REPO_ROOT / "services/layer4-agents/src/layer4_agents/registry/api/routes.py"


def test_registry_service_enforces_environment_stage_policy() -> None:
    content = REGISTRY_SERVICE.read_text(encoding="utf-8")
    assert "ALLOWED_MODEL_STAGES" in content
    for stage in ("dev", "staging", "production", "deprecated"):
        assert f'"{stage}"' in content or f"'{stage}'" in content
    assert "allowed_transitions" in content
    assert "Forbidden stage transition" in content


def test_registry_service_emits_model_promotion_audit_events() -> None:
    content = REGISTRY_SERVICE.read_text(encoding="utf-8")
    assert "AuditAction.MODEL_PROMOTED" in content
    assert "AuditAction.MODEL_DEPRECATED" in content
    assert "emit_audit_event(" in content


def test_registry_eval_run_emits_eval_audit_event() -> None:
    content = REGISTRY_ROUTES.read_text(encoding="utf-8")
    assert "AuditAction.MODEL_EVALUATED" in content
    assert "eval_score" in content
