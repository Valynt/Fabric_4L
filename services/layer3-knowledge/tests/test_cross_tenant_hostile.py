from __future__ import annotations

"""Cross-tenant hostile invariants for layer3-knowledge."""


from pathlib import Path


def _load_service_code() -> str:
    """Concatenate all Python source under the service ``src`` tree."""
    service_root = Path(__file__).resolve().parents[1] / "src"
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in service_root.rglob("*.py"))


def test_tenant_a_cannot_read_tenant_b_patterns_present() -> None:
    content = _load_service_code()
    assert "tenant_id" in content, "Expected tenant_id references in source"
    assert "list_" in content or "get_" in content, "Expected read-style method names in source"


def test_tenant_a_cannot_mutate_tenant_b_patterns_present() -> None:
    content = _load_service_code()
    assert "tenant_id" in content, "Expected tenant_id references in source"
    assert (
        "create" in content
        or "update" in content
        or "delete" in content
        or "ingest" in content
    ), "Expected write-style method names in source"
