"""V1-TENANCY-011: Hostile + allowed tests for GDPR deletion/export endpoints.

Covers, against ``services/api/src/gdpr/routes.py``:

* A tenant admin of tenant B must not initiate a deletion job against
  tenant A (cross-tenant lifecycle operation).
* A tenant admin of tenant B must not read tenant A's deletion job status
  or report by guessing/enumerating ``request_id``.
* 404-vs-403 uniformity: a request for another tenant's job must be
  indistinguishable from a request for a job that does not exist (no
  cross-tenant existence oracle).
* HTTP error responses must not leak raw exception text.

Self-contained: sqlalchemy and the internal ``value_fabric.*`` service
modules are stubbed in sys.modules; the route handlers are invoked directly
with fake admin contexts and a fake BackgroundTasks.
"""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_API_SRC = _PROJECT_ROOT / "services" / "api" / "src"


def _install_stubs() -> None:
    # --- sqlalchemy ------------------------------------------------------
    sqlalchemy_mod = types.ModuleType("sqlalchemy")
    sqlalchemy_mod.text = lambda q: q  # type: ignore[attr-defined]
    sqlalchemy_async_mod = types.ModuleType("sqlalchemy.ext.asyncio")

    class _AsyncSession:  # noqa: D401 - stub
        pass

    sqlalchemy_async_mod.AsyncSession = _AsyncSession  # type: ignore[attr-defined]
    sqlalchemy_ext_mod = types.ModuleType("sqlalchemy.ext")
    sys.modules.setdefault("sqlalchemy", sqlalchemy_mod)
    sys.modules.setdefault("sqlalchemy.ext", sqlalchemy_ext_mod)
    sys.modules.setdefault("sqlalchemy.ext.asyncio", sqlalchemy_async_mod)

    # --- value_fabric service modules ------------------------------------
    vf = types.ModuleType("value_fabric")
    vf.__path__ = []  # type: ignore[attr-defined]

    vf_db = types.ModuleType("value_fabric.db")
    vf_db.get_db_session = MagicMock()  # type: ignore[attr-defined]

    vf_config = types.ModuleType("value_fabric.config")
    vf_config.settings = types.SimpleNamespace()  # type: ignore[attr-defined]

    vf_cache = types.ModuleType("value_fabric.cache")
    vf_cache.get_redis = AsyncMock()  # type: ignore[attr-defined]

    vf_audit = types.ModuleType("value_fabric.audit")
    vf_audit.append_audit_record = AsyncMock()  # type: ignore[attr-defined]
    vf_audit.log_audit_event = AsyncMock()  # type: ignore[attr-defined]

    vf_auth = types.ModuleType("value_fabric.auth")
    vf_auth.require_admin = MagicMock()  # type: ignore[attr-defined]
    vf_auth.get_current_user = MagicMock()  # type: ignore[attr-defined]

    sys.modules.setdefault("value_fabric", vf)
    sys.modules.setdefault("value_fabric.db", vf_db)
    sys.modules.setdefault("value_fabric.config", vf_config)
    sys.modules.setdefault("value_fabric.cache", vf_cache)
    sys.modules.setdefault("value_fabric.audit", vf_audit)
    sys.modules.setdefault("value_fabric.auth", vf_auth)


_install_stubs()
sys.path.insert(0, str(_API_SRC))

from fastapi import HTTPException  # noqa: E402

from gdpr import routes  # noqa: E402
from gdpr.deletion import DeletionReport  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _tenant_admin(tenant_id: str) -> dict[str, Any]:
    return {
        "user_id": f"admin-{tenant_id}",
        "tenant_id": tenant_id,
        "roles": ["tenant_admin"],
        "permissions": [],
    }


def _super_admin() -> dict[str, Any]:
    return {
        "user_id": "platform-admin",
        "tenant_id": None,
        "roles": ["super_admin"],
        "permissions": [],
    }


def _delete_body(tenant_id: str) -> routes.DeleteTenantRequest:
    return routes.DeleteTenantRequest(
        tenant_id=tenant_id,
        confirmation=f"delete {tenant_id}",
        reason="regulatory erasure request",
    )


class _FakeBackgroundTasks:
    def __init__(self) -> None:
        self.tasks: list[tuple[Any, tuple, dict]] = []

    def add_task(self, func, *args, **kwargs) -> None:
        self.tasks.append((func, args, kwargs))


# ---------------------------------------------------------------------------
# Hostile: cross-tenant deletion initiation.
# ---------------------------------------------------------------------------

class TestCrossTenantDeletionInitiation:
    def test_tenant_admin_cannot_delete_other_tenants_data(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tenant B admin targeting tenant A must be denied (fail closed)."""
        monkeypatch.setattr(
            routes, "list_deletion_jobs_for_tenant", AsyncMock(return_value=[])
        )
        tasks = _FakeBackgroundTasks()
        with pytest.raises(HTTPException) as excinfo:
            _run(
                routes.initiate_deletion(
                    body=_delete_body("tenant-a"),
                    background_tasks=tasks,
                    admin=_tenant_admin("tenant-b"),
                )
            )
        assert excinfo.value.status_code in (403, 404)
        # No background deletion may have been scheduled.
        assert tasks.tasks == []

    def test_tenant_admin_can_delete_own_tenant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            routes, "list_deletion_jobs_for_tenant", AsyncMock(return_value=[])
        )
        tasks = _FakeBackgroundTasks()
        resp = _run(
            routes.initiate_deletion(
                body=_delete_body("tenant-b"),
                background_tasks=tasks,
                admin=_tenant_admin("tenant-b"),
            )
        )
        assert resp.tenant_id == "tenant-b"
        assert len(tasks.tasks) == 1

    def test_cross_tenant_denial_does_not_leak_exception_text(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            routes, "list_deletion_jobs_for_tenant", AsyncMock(return_value=[])
        )
        with pytest.raises(HTTPException) as excinfo:
            _run(
                routes.initiate_deletion(
                    body=_delete_body("tenant-a"),
                    background_tasks=_FakeBackgroundTasks(),
                    admin=_tenant_admin("tenant-b"),
                )
            )
        detail = str(excinfo.value.detail).lower()
        assert "traceback" not in detail
        assert "error:" not in detail


# ---------------------------------------------------------------------------
# Hostile: cross-tenant status/report reads + existence oracle.
# ---------------------------------------------------------------------------

class TestCrossTenantJobReads:
    def _tenant_a_job(self) -> tuple[DeletionReport, str]:
        return (
            DeletionReport(
                tenant_id="tenant-a",
                request_id="req-a-123",
                initiated_by="admin-tenant-a",
            ),
            "regulatory erasure request",
        )

    def test_tenant_b_cannot_read_tenant_a_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            routes, "get_deletion_job", AsyncMock(return_value=self._tenant_a_job())
        )
        with pytest.raises(HTTPException) as excinfo:
            _run(routes.get_deletion_status("req-a-123", admin=_tenant_admin("tenant-b")))
        assert excinfo.value.status_code == 404

    def test_tenant_b_cannot_read_tenant_a_report(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            routes, "get_deletion_job", AsyncMock(return_value=self._tenant_a_job())
        )
        with pytest.raises(HTTPException) as excinfo:
            _run(routes.get_deletion_report("req-a-123", admin=_tenant_admin("tenant-b")))
        assert excinfo.value.status_code == 404

    def test_cross_tenant_read_indistinguishable_from_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """404-vs-403 must not reveal cross-tenant existence."""
        # Case 1: job exists but belongs to tenant A.
        monkeypatch.setattr(
            routes, "get_deletion_job", AsyncMock(return_value=self._tenant_a_job())
        )
        with pytest.raises(HTTPException) as cross:
            _run(routes.get_deletion_status("req-a-123", admin=_tenant_admin("tenant-b")))
        # Case 2: job does not exist at all.
        monkeypatch.setattr(
            routes, "get_deletion_job", AsyncMock(return_value=(None, ""))
        )
        with pytest.raises(HTTPException) as missing:
            _run(routes.get_deletion_status("req-nope", admin=_tenant_admin("tenant-b")))
        assert cross.value.status_code == missing.value.status_code == 404

    def test_owning_tenant_admin_can_read_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            routes, "get_deletion_job", AsyncMock(return_value=self._tenant_a_job())
        )
        resp = _run(routes.get_deletion_status("req-a-123", admin=_tenant_admin("tenant-a")))
        assert resp.request_id == "req-a-123"
        assert resp.tenant_id == "tenant-a"

    def test_super_admin_can_read_any_status(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            routes, "get_deletion_job", AsyncMock(return_value=self._tenant_a_job())
        )
        resp = _run(routes.get_deletion_status("req-a-123", admin=_super_admin()))
        assert resp.tenant_id == "tenant-a"
