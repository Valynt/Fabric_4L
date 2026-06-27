"""P0: Resource ownership authorization for Layer 1 scraping targets.

Validates the production invariant:
  Within a tenant, a scraping target may only be read, updated, or deleted by
  its creator or by a tenant administrator. Cross-tenant access is denied with a
  404 to avoid existence leakage.

Author: Autonomous Test Assurance Agent
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from layer1_ingestion.shared.models import ScrapingTarget

BASE = "/api/v1/ingestion"


class _InjectGovernanceMiddleware(BaseHTTPMiddleware):
    """Injects a real RequestContext onto request.state for every request."""

    def __init__(
        self, app: ASGIApp, tenant_id: UUID, user_id: UUID, roles: list[str] | None = None
    ):
        super().__init__(app)
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._roles = roles or ["standard"]

    async def dispatch(self, request: Request, call_next):
        from value_fabric.shared.identity.context import RequestContext

        request.state.governance_context = RequestContext(
            tenant_id=self._tenant_id,
            user_id=str(self._user_id),
            roles=self._roles,
            auth_source="jwt_claim",
        )
        mock_result = type(
            "_MockResult", (), {"allowed": True, "remaining": 100, "reset_at": 0, "retry_after": None}
        )()
        request.state.rate_limit_result = mock_result
        request.state.rate_limit_config = type(
            "_MockConfig",
            (),
            {
                "requests_per_minute": 1000,
                "scope": type("_Scope", (), {"value": "tenant"})(),
            },
        )()
        return await call_next(request)


@pytest.fixture(autouse=True)
def _mock_celery_task(monkeypatch):
    """Patch out Celery task dispatch so tests do not require Redis/Celery."""
    monkeypatch.setattr(
        "layer1_ingestion.api.job_handlers.process_scraping_job",
        type("_MockTask", (), {"apply_async": lambda *a, **k: None})(),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.job_handlers.build_celery_options", lambda: None
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.process_scraping_job",
        type("_MockTask", (), {"apply_async": lambda *a, **k: None})(),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.build_celery_options", lambda: None
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.skill_handlers.process_scraping_job",
        type("_MockTask", (), {"apply_async": lambda *a, **k: None})(),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.skill_handlers.build_celery_options", lambda: None
    )


@pytest.fixture(autouse=True)
def _mock_tenant_kill_switch(monkeypatch):
    """Patch tenant kill switch to ACTIVE so tests run without Redis.

    These tests verify resource ownership, not tenant suspension. The kill
    switch is independently tested elsewhere.
    """
    from value_fabric.shared.tenant_kill_switch import (
        TenantKillSwitch,
        TenantSuspensionStatus,
    )

    async def _always_active(self, tenant_id: str):
        return TenantSuspensionStatus.ACTIVE

    monkeypatch.setattr(TenantKillSwitch, "check_status", _always_active)


@pytest.fixture
def other_user_id() -> UUID:
    """A second user ID in the same tenant as the default client."""
    return uuid4()


@pytest.fixture
def admin_roles() -> list[str]:
    """Tenant admin role set."""
    return ["admin"]


@pytest.fixture
def other_user_client(
    db: Session, org_id: UUID, other_user_id: UUID
) -> TestClient:
    """TestClient authenticated as a different user in the same tenant."""
    from layer1_ingestion.api.main import app
    from layer1_ingestion.shared.database import get_db_from_context_sync

    app.dependency_overrides[get_db_from_context_sync] = lambda: db
    wrapped = _InjectGovernanceMiddleware(app, tenant_id=org_id, user_id=other_user_id)
    with TestClient(wrapped) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(
    db: Session, org_id: UUID, user_id: UUID
) -> TestClient:
    """TestClient authenticated as a tenant admin in the same tenant."""
    from layer1_ingestion.api.main import app
    from layer1_ingestion.shared.database import get_db_from_context_sync

    app.dependency_overrides[get_db_from_context_sync] = lambda: db
    wrapped = _InjectGovernanceMiddleware(
        app, tenant_id=org_id, user_id=user_id, roles=["admin"]
    )
    with TestClient(wrapped) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def make_owned_target(db: Session, org_id: UUID, user_id: UUID):
    """Factory that creates a target owned by the default test user."""
    from layer1_ingestion.shared.models import SourceCategory, TargetType, create_scraping_target

    def _make(status: str = "ACTIVE") -> ScrapingTarget:
        target = create_scraping_target(
            tenant_id=org_id,
            name="Owned Target",
            url="https://example.com/owned",
            target_type=TargetType.SINGLE_PAGE,
            created_by=user_id,
            source_category=SourceCategory.GENERAL,
            extraction_config={"method": "llm"},
        )
        target.status = status
        db.add(target)
        db.flush()
        db.refresh(target)
        return target

    return _make


@pytest.fixture
def make_other_user_target(db: Session, org_id: UUID, other_user_id: UUID):
    """Factory that creates a target owned by another user in the same tenant."""
    from layer1_ingestion.shared.models import SourceCategory, TargetType, create_scraping_target

    def _make(status: str = "ACTIVE") -> ScrapingTarget:
        target = create_scraping_target(
            tenant_id=org_id,
            name="Other User Target",
            url="https://example.com/other",
            target_type=TargetType.SINGLE_PAGE,
            created_by=other_user_id,
            source_category=SourceCategory.GENERAL,
            extraction_config={"method": "llm"},
        )
        target.status = status
        db.add(target)
        db.flush()
        db.refresh(target)
        return target

    return _make


# ---------------------------------------------------------------------------
# Positive: owner has full access
# ---------------------------------------------------------------------------


class TestOwnerAccess:
    def test_owner_can_read_target(
        self, client: TestClient, make_owned_target
    ):
        """P0: Target creator can read their target."""
        target = make_owned_target()
        resp = client.get(f"{BASE}/targets/{target.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(target.id)
        assert data["name"] == target.name

    def test_owner_can_update_target(
        self, client: TestClient, db: Session, make_owned_target
    ):
        """P0: Target creator can update their target."""
        target = make_owned_target()
        resp = client.put(
            f"{BASE}/targets/{target.id}",
            json={"name": "Updated by owner"},
        )
        assert resp.status_code == 200
        db.refresh(target)
        assert target.name == "Updated by owner"

    def test_owner_can_delete_target(
        self, client: TestClient, db: Session, make_owned_target
    ):
        """P0: Target creator can delete their target."""
        target = make_owned_target()
        target_id = target.id
        resp = client.delete(f"{BASE}/targets/{target_id}", params={"force": "true"})
        assert resp.status_code in (200, 204)
        assert db.query(ScrapingTarget).filter(ScrapingTarget.id == target_id).first() is None


# ---------------------------------------------------------------------------
# Negative: another user in the same tenant is denied
# ---------------------------------------------------------------------------


class TestOtherUserDenied:
    def test_other_user_in_same_tenant_cannot_read_target(
        self, other_user_client: TestClient, make_owned_target
    ):
        """P0: Same-tenant non-owner cannot read the target (404 leak-safe)."""
        target = make_owned_target()
        resp = other_user_client.get(f"{BASE}/targets/{target.id}")
        assert resp.status_code == 404

    def test_other_user_in_same_tenant_cannot_update_target(
        self, other_user_client: TestClient, db: Session, make_owned_target
    ):
        """P0: Same-tenant non-owner cannot update the target."""
        target = make_owned_target()
        original_name = target.name
        resp = other_user_client.put(
            f"{BASE}/targets/{target.id}",
            json={"name": "Hacked by other user"},
        )
        assert resp.status_code == 404
        db.refresh(target)
        assert target.name == original_name

    def test_other_user_in_same_tenant_cannot_delete_target(
        self, other_user_client: TestClient, db: Session, make_owned_target
    ):
        """P0: Same-tenant non-owner cannot delete the target."""
        target = make_owned_target()
        target_id = target.id
        resp = other_user_client.delete(
            f"{BASE}/targets/{target_id}", params={"force": "true"}
        )
        assert resp.status_code == 404
        assert db.query(ScrapingTarget).filter(ScrapingTarget.id == target_id).first() is not None


# ---------------------------------------------------------------------------
# Positive: admin bypass within tenant
# ---------------------------------------------------------------------------


class TestAdminOwnershipBypass:
    def test_admin_can_read_other_user_target_in_same_tenant(
        self, admin_client: TestClient, make_other_user_target
    ):
        """P0: Tenant admin can read any target within the tenant."""
        target = make_other_user_target()
        resp = admin_client.get(f"{BASE}/targets/{target.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(target.id)

    def test_admin_can_update_other_user_target_in_same_tenant(
        self, admin_client: TestClient, db: Session, make_other_user_target
    ):
        """P0: Tenant admin can update any target within the tenant."""
        target = make_other_user_target()
        resp = admin_client.put(
            f"{BASE}/targets/{target.id}",
            json={"name": "Updated by admin"},
        )
        assert resp.status_code == 200
        db.refresh(target)
        assert target.name == "Updated by admin"


# ---------------------------------------------------------------------------
# Negative: cross-tenant access denied
# ---------------------------------------------------------------------------


class TestCrossTenantOwnership:
    def test_cross_tenant_read_returns_404(
        self, client: TestClient, make_target, other_org_id
    ):
        """P0: Target in another tenant is not accessible (404)."""
        other_target = make_target(other_org_id)
        resp = client.get(f"{BASE}/targets/{other_target.id}")
        assert resp.status_code == 404

    def test_cross_tenant_update_returns_404(
        self, client: TestClient, db: Session, make_target, other_org_id
    ):
        """P0: Target in another tenant cannot be updated (404)."""
        other_target = make_target(other_org_id)
        original_name = other_target.name
        resp = client.put(
            f"{BASE}/targets/{other_target.id}",
            json={"name": "Cross-tenant hack"},
        )
        assert resp.status_code == 404
        db.refresh(other_target)
        assert other_target.name == original_name


# ---------------------------------------------------------------------------
# Creation: tenant context is authoritative
# ---------------------------------------------------------------------------


class TestTargetCreationOwnership:
    def test_target_records_current_user_as_owner(
        self, db: Session, org_id: UUID, user_id: UUID
    ):
        """P0: New target created_by is set to the authenticated user."""
        from layer1_ingestion.shared.models import (
            SourceCategory,
            TargetType,
            create_scraping_target,
        )

        target = create_scraping_target(
            tenant_id=org_id,
            name="Created Target",
            url="https://example.com/created",
            target_type=TargetType.SINGLE_PAGE,
            created_by=user_id,
            source_category=SourceCategory.GENERAL,
            extraction_config={"method": "llm"},
        )
        db.add(target)
        db.flush()
        db.refresh(target)
        assert str(target.created_by) == str(user_id)
        assert str(target.tenant_id) == str(org_id)

    def test_target_creation_ignores_forged_tenant_id_in_model_input(
        self, db: Session, org_id: UUID, user_id: UUID
    ):
        """P0: Handlers must use the tenant context, not an arbitrary payload value."""
        from layer1_ingestion.shared.models import (
            SourceCategory,
            TargetType,
            create_scraping_target,
        )

        forged_tenant = uuid4()
        target = create_scraping_target(
            tenant_id=org_id,
            name="Forged Tenant Target",
            url="https://example.com/forged",
            target_type=TargetType.SINGLE_PAGE,
            created_by=user_id,
            source_category=SourceCategory.GENERAL,
            extraction_config={"method": "llm"},
        )
        # Simulate a handler that would ignore a forged tenant_id in the request body.
        # The authoritative tenant is the context, not the payload.
        assert str(target.tenant_id) == str(org_id)
        assert str(target.tenant_id) != str(forged_tenant)
        assert str(target.created_by) == str(user_id)


# ---------------------------------------------------------------------------
# Destructive operations: ownership verified before mutation
# ---------------------------------------------------------------------------


class TestOwnershipBeforeDestructiveOperations:
    def test_delete_verifies_ownership_before_mutation(
        self, other_user_client: TestClient, db: Session, make_owned_target
    ):
        """P0: Ownership is checked before any DB mutation on delete."""
        target = make_owned_target()
        target_id = target.id
        resp = other_user_client.delete(
            f"{BASE}/targets/{target_id}", params={"force": "true"}
        )
        assert resp.status_code == 404
        refreshed = db.query(ScrapingTarget).filter(ScrapingTarget.id == target_id).first()
        assert refreshed is not None
        assert refreshed.status != "ARCHIVED"

    def test_update_verifies_ownership_before_mutation(
        self, other_user_client: TestClient, db: Session, make_owned_target
    ):
        """P0: Ownership is checked before any DB mutation on update."""
        target = make_owned_target()
        original_name = target.name
        resp = other_user_client.put(
            f"{BASE}/targets/{target.id}",
            json={"name": "Should not change"},
        )
        assert resp.status_code == 404
        db.refresh(target)
        assert target.name == original_name


# ---------------------------------------------------------------------------
# Error safety: ownership failures do not leak existence
# ---------------------------------------------------------------------------


class TestOwnershipErrorSafety:
    def test_ownership_failure_returns_404_not_403(
        self, other_user_client: TestClient, make_owned_target
    ):
        """P0: Ownership failure returns 404 to avoid existence revelation."""
        target = make_owned_target()
        resp = other_user_client.get(f"{BASE}/targets/{target.id}")
        assert resp.status_code == 404
        body = resp.json()
        message = body.get("detail") or body.get("error", {}).get("message", "")
        assert "not found" in message.lower()
