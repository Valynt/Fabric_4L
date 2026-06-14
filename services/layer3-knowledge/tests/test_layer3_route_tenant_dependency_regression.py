"""Regression tests for canonical tenant dependency in Layer 3 route handlers."""

from pathlib import Path

ROUTES = {
    "src/api/routes/knowledge.py",
    "src/api/routes/variables.py",
    "src/api/routes/formulas.py",
}


def test_routes_use_canonical_tenant_dependency() -> None:
    for rel in ROUTES:
        content = Path(rel).read_text(encoding="utf-8")
        assert "require_tenant_context" in content, f"{rel} must inject require_tenant_context"


def test_routes_do_not_fallback_to_api_key_tenant_attrs() -> None:
    forbidden = [
        'getattr(api_key, "tenant_id"',
        "getattr(api_key, 'tenant_id'",
        "api_key.tenant_id",
        "_get_authenticated_tenant_id(api_key)",
    ]
    for rel in ROUTES:
        content = Path(rel).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"{rel} still contains legacy tenant fallback token: {token}"
