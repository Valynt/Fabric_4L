"""Static guard: no RLS GUC bypass in fabric_api_records migrations, and no
silent migration fallback onto the Layer 5 ground_truth database.

Background (V1-DISCOVERY-000, findings D-12/D-2):
- The raw baseline 0002_fabric_api_records_jsonb_bridge.sql created an RLS
  policy with an ``IN ('admin', 'internal', 'system')`` escape hatch. The live
  Alembic chain already closed it in 6f3b9c2d4a91 (FORCE RLS + exact-tenant
  policy with WITH CHECK). This guard keeps the baseline aligned and blocks
  reintroduction anywhere in the api migration tree.
- services/layer4-agents/migrations/env.py fell back to
  CHECKPOINT_DATABASE_URL (the Layer 5 ground_truth database) when
  LAYER4_DATABASE_URL was unset, so a migrate run with compose env vars would
  silently apply the Layer 4 revision chain to a database Layer 4 does not
  own. The fallback is removed; this guard keeps it removed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.p0, pytest.mark.tenant_boundary, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
API_MIGRATIONS = REPO_ROOT / "services" / "api" / "migrations" / "versions"
L4_ALEMBIC_ENV = REPO_ROOT / "services" / "layer4-agents" / "migrations" / "env.py"
RAW_BASELINE = API_MIGRATIONS / "0002_fabric_api_records_jsonb_bridge.sql"

_BYPASS_SENTINELS = (
    "'admin', 'internal', 'system'",
    '"admin", "internal", "system"',
)


def _migration_texts() -> dict[str, str]:
    paths = sorted(
        {*API_MIGRATIONS.glob("*.sql"), *API_MIGRATIONS.glob("*.py")},
        key=lambda p: p.name,
    )
    return {
        path.name: path.read_text(encoding="utf-8", errors="replace")
        for path in paths
        if path.name != "__init__.py"
    }


def test_no_rls_guc_bypass_in_any_api_migration() -> None:
    """No migration (upgrade or downgrade SQL) may contain an
    admin/internal/system tenant bypass — even in downgrade bodies, which must
    restore the pre-force exact-tenant policy, never the GUC bypass."""
    offenders = []
    for name, text in _migration_texts().items():
        for sentinel in _BYPASS_SENTINELS:
            if sentinel in text:
                offenders.append(f"{name}: bypass sentinel present ({sentinel})")
    assert not offenders, (
        "RLS GUC bypass detected in API migrations — the fabric_api_records "
        "policy must fail closed on the exact tenant only:\n" + "\n".join(sorted(set(offenders)))
    )


def test_raw_baseline_matches_closed_live_policy() -> None:
    """0002.sql must mirror the closed policy from revision 6f3b9c2d4a91."""
    text = RAW_BASELINE.read_text(encoding="utf-8")
    assert "FORCE ROW LEVEL SECURITY" in text, "baseline must FORCE RLS like the live chain"
    assert "WITH CHECK" in text, "baseline must include a WITH CHECK tenant predicate"
    assert "current_setting('app.tenant_id', true)" in text
    for sentinel in _BYPASS_SENTINELS:
        assert sentinel not in text, f"baseline reintroduces GUC bypass: {sentinel}"


def test_layer4_alembic_env_has_no_checkpoint_fallback() -> None:
    """env.py must fail closed without an explicit Layer 4 DSN — never fall
    back to CHECKPOINT_DATABASE_URL (the Layer 5 ground_truth database)."""
    text = L4_ALEMBIC_ENV.read_text(encoding="utf-8")
    assert 'os.environ.get("CHECKPOINT_DATABASE_URL")' not in text, (
        "env.py must not use CHECKPOINT_DATABASE_URL as a migration fallback; "
        "doing so applies the Layer 4 revision chain to the Layer 5 database"
    )
    assert "LAYER4_DATABASE_URL_SYNC" in text, (
        "env.py must name LAYER4_DATABASE_URL_SYNC in its explicit configuration path"
    )
