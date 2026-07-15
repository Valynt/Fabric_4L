from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_critical_flows_use_canonical_tenant_guc() -> None:
    source = (ROOT / "tests" / "integration" / "critical_flows.py").read_text(encoding="utf-8")

    assert "app.current_tenant_id" not in source
    assert "set_config('app.tenant_id'" in source


def test_fabric_auth_rls_helper_preserves_canonical_tenant_guc() -> None:
    source = (
        ROOT
        / "packages"
        / "shared"
        / "src"
        / "value_fabric"
        / "shared"
        / "identity"
        / "fabric_auth"
        / "rls.py"
    ).read_text(encoding="utf-8")

    assert 'TENANT_GUC = "app.tenant_id"' in source
    assert "set_config(:k, :v, true)" in source
    assert "auth.tenant_id" in source
