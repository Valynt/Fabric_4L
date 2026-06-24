from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPATIBILITY_ROUTES = (
    REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/routes/compatibility.py",
)


def test_layer1_compatibility_routes_emit_non_pii_deprecation_telemetry() -> None:
    for route_file in COMPATIBILITY_ROUTES:
        source = route_file.read_text(encoding="utf-8")
        assert "legacy_route_deprecation_usage" in source
        assert "tenant_hash" in source
        assert "account_hash" in source
        assert "canonical_route" in source
        assert "timestamp" in source
        assert "tenant_id=tenant_id" not in source
        assert "user_id=user_id" not in source
