from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BYPASS_MARKER = "INTENTIONAL_DB_ADAPTER_BYPASS = True"


def _runtime_bypass_modules() -> list[Path]:
    candidates = [
        *ROOT.glob("services/*/src/**/database.py"),
        *ROOT.glob("value_fabric/layer*/**/database*.py"),
    ]
    return sorted(
        {
            path
            for path in candidates
            if BYPASS_MARKER in path.read_text(encoding="utf-8")
            and not path.relative_to(ROOT).parts[0] == "tests"
        }
    )


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.contract_static
@pytest.mark.production_db_invariant
@pytest.mark.parametrize(
    "module_path", _runtime_bypass_modules(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_intentional_db_adapter_bypass_modules_enforce_production_url_policy(
    module_path: Path,
) -> None:
    source = _source(module_path)

    assert (
        "_assert_rls_safe_database_url" in source
    ), f"{module_path.relative_to(ROOT)} must keep an explicit production URL policy guard."
    assert (
        "_is_production_like_runtime" in source
    ), f"{module_path.relative_to(ROOT)} must fail fast in production-like runtime mode."
    assert (
        "_RLS_SUPPORTED_SCHEMES" in source and "postgresql" in source
    ), f"{module_path.relative_to(ROOT)} must allow only PostgreSQL-capable schemes for production RLS."
    assert (
        "_RLS_SUPERUSER_NAMES" in source and "postgres" in source
    ), f"{module_path.relative_to(ROOT)} must reject PostgreSQL superuser roles in production."
    assert re.search(
        r"scheme\s+not\s+in\s+_RLS_SUPPORTED_SCHEMES", source
    ), f"{module_path.relative_to(ROOT)} must reject non-PostgreSQL schemes, not just document them."
    assert re.search(
        r"username\s+in\s+_RLS_SUPERUSER_NAMES", source
    ), f"{module_path.relative_to(ROOT)} must reject RLS-bypassing superuser roles."


@pytest.mark.contract_static
@pytest.mark.production_db_invariant
@pytest.mark.parametrize(
    "module_path", _runtime_bypass_modules(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_intentional_db_adapter_bypass_modules_set_transaction_local_tenant_context(
    module_path: Path,
) -> None:
    source = _source(module_path).lower()

    assert (
        "app.tenant_id" in source
    ), f"{module_path.relative_to(ROOT)} must set the PostgreSQL app.tenant_id runtime parameter."
    assert (
        "set local app.tenant_id" in source
        or "set_config('app.tenant_id'" in source
        or 'set_config("app.tenant_id"' in source
    ), f"{module_path.relative_to(ROOT)} must use transaction-local SET LOCAL/set_config(..., true) tenant context."
    assert (
        "_mark_session_tenant_context" in source
    ), f"{module_path.relative_to(ROOT)} must record tenant-context state on the session for fail-closed guards."


@pytest.mark.contract_static
@pytest.mark.production_db_invariant
@pytest.mark.parametrize(
    "module_path", _runtime_bypass_modules(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_intentional_db_adapter_bypass_modules_keep_pool_defaults(
    module_path: Path,
) -> None:
    source = _source(module_path)

    for required in ("pool_size", "max_overflow", "pool_pre_ping"):
        assert (
            required in source
        ), f"{module_path.relative_to(ROOT)} must configure {required}."
    assert (
        "pool_timeout" in source or "statement_timeout" in source
    ), f"{module_path.relative_to(ROOT)} must bound connection or statement wait time."


@pytest.mark.contract_static
@pytest.mark.production_db_invariant
@pytest.mark.parametrize(
    "module_path", _runtime_bypass_modules(), ids=lambda p: str(p.relative_to(ROOT))
)
def test_intentional_db_adapter_bypass_modules_fail_closed_without_tenant(
    module_path: Path,
) -> None:
    source = _source(module_path)

    assert (
        "TenantContextError" in source
    ), f"{module_path.relative_to(ROOT)} must expose a tenant-context failure mode."
    assert (
        "validate_tenant_id" in source and "tenant_id is None" in source
    ), f"{module_path.relative_to(ROOT)} must validate missing tenant IDs explicitly."
    assert (
        "get_db_from_context" in source
    ), f"{module_path.relative_to(ROOT)} must expose a context-derived tenant DB dependency."
    assert (
        "tenant context required" in source.lower()
        or "authentication required" in source.lower()
    ), f"{module_path.relative_to(ROOT)} must reject requests that lack authenticated tenant context."
