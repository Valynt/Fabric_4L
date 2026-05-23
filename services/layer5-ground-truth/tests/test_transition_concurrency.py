import uuid

import pytest
from layer5_ground_truth import database as db_module
from layer5_ground_truth.api.auth import TokenClaims, get_current_user
from layer5_ground_truth.api.main import create_app
from layer5_ground_truth.database import get_db_from_context
from layer5_ground_truth.models.truth_object import ValidationEvent
from sqlalchemy import select


@pytest.mark.anyio
async def test_concurrent_transition_conflict_is_deterministic(engine):
    factory = db_module.get_session_factory()
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    async with factory() as seed:
        create_resp = await create_app_client(seed, tenant_id).post(
            "/api/v1/truths",
            json={
                "claim": "Invoice reconciliation costs 20h/month",
                "claim_type": "efficiency_gain",
                "confidence": 0.9,
                "sources": [
                    {"source_type": "crm_record", "source_url": "https://example.com/1"},
                    {"source_type": "call_transcript", "source_url": "https://example.com/2"},
                ],
            },
        )
        assert create_resp.status_code == 201
        truth_id = create_resp.json()["id"]

    # Two isolated sessions read the same state then try same transition.
    async with factory() as s1, factory() as s2:
        c1 = await create_app_client(s1, tenant_id)
        c2 = await create_app_client(s2, tenant_id)

        p = {"action": "validate", "actor": "reviewer@tenant-a.com", "actor_type": "human"}
        r1 = await c1.post(f"/api/v1/truths/{truth_id}/validate", json=p)
        r2 = await c2.post(f"/api/v1/truths/{truth_id}/validate", json=p)

        statuses = sorted([r1.status_code, r2.status_code])
        assert statuses == [200, 409]
        conflict = r1 if r1.status_code == 409 else r2
        assert conflict.json()["detail"]["code"] == "TRANSITION_CONFLICT"

    async with factory() as verify:
        q = await verify.execute(
            select(ValidationEvent).where(ValidationEvent.truth_object_id == uuid.UUID(truth_id))
        )
        events = list(q.scalars().all())
        # initial extracted + exactly one successful transition
        assert len(events) == 2
        # Count validated events (may include auto-advance + manual validate)
        assert sum(1 for e in events if e.to_status == "validated") >= 1


@pytest.mark.anyio
async def test_cross_tenant_transition_isolation_no_leakage(engine):
    factory = db_module.get_session_factory()
    tenant_a = uuid.UUID("00000000-0000-0000-0000-000000000001")
    tenant_b = uuid.UUID("00000000-0000-0000-0000-000000000002")

    async with factory() as seed:
        create_resp = await create_app_client(seed, tenant_a).post(
            "/api/v1/truths",
            json={"claim": "A only", "claim_type": "efficiency_gain", "confidence": 0.8},
        )
        assert create_resp.status_code == 201
        truth_id = create_resp.json()["id"]

    async with factory() as s:
        r = await (await create_app_client(s, tenant_b)).post(
            f"/api/v1/truths/{truth_id}/validate",
            json={"action": "validate", "actor": "b@tenant.com", "actor_type": "human"},
        )
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()


async def create_app_client(db_session, tenant_id):
    from httpx import ASGITransport, AsyncClient

    app = create_app()

    async def override_get_db_from_context():
        yield db_session

    def override_get_current_user():
        return TokenClaims(tenant_id=tenant_id, user_id="tester", roles=["admin"])

    app.dependency_overrides[get_db_from_context] = override_get_db_from_context
    app.dependency_overrides[get_current_user] = override_get_current_user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
