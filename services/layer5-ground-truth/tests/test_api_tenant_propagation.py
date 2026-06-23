from __future__ import annotations

"""Tenant context propagation guardrails for layer5-ground-truth."""


from pathlib import Path


def _load_service_code() -> str:
    """Concatenate all Python source under the service ``src`` tree."""
    service_root = Path(__file__).resolve().parents[1] / "src"
    py_files = list(service_root.rglob("*.py"))
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in py_files)


def test_repository_calls_use_context_tenant_id() -> None:
    """Enforce trusted context propagation by checking canonical route code."""
    content = _load_service_code()
    assert (
        "tenant_id=ctx.tenant_id" in content or "tenant_id=context.tenant_id" in content
        or "tenant_id=caller.tenant_id" in content
    ), "Expected tenant_id propagated from trusted context object"


def test_missing_tenant_context_has_fail_closed_guard() -> None:
    content = _load_service_code()
    assert (
        "Tenant context required" in content
        or "require_tenant_context" in content
        or "HTTPException(status_code=401" in content
    ), "Expected fail-closed guard for missing tenant context"
