"""
Integration tests for the Layer 5 Ground Truth API endpoints.

Tests use httpx.AsyncClient against the real FastAPI app with a
SQLite in-memory database. Each test starts with a clean state
(transaction is rolled back after each test via the db fixture).

Coverage:
  POST   /api/v1/truths                  — create
  GET    /api/v1/truths                  — list with filters
  GET    /api/v1/truths/{id}             — get by ID
  POST   /api/v1/truths/{id}/validate    — state transitions
  POST   /api/v1/truths/{id}/sources     — add source
  DELETE /api/v1/truths/{id}             — soft delete
  GET    /api/v1/truths/{id}/audit       — audit trail
  POST   /api/v1/truths/sync-kg         — KG sync
  GET    /api/v1/maturity-ladder         — reference endpoint
  GET    /health                         — health check
"""

import os
import uuid

import pytest

from tests.conftest import TEST_ORG_ID, make_source_payload, make_truth_payload

ORG_PARAM = f"?tenant_id={TEST_ORG_ID}"


# ---------------------------------------------------------------------------
# POST /api/v1/truths
# ---------------------------------------------------------------------------


class TestCreateTruth:
    @pytest.mark.asyncio
    async def test_creates_truth_object(self, client):
        """Should create a TruthObject and return 201."""
        payload = make_truth_payload()
        resp = await client.post(f"/api/v1/truths{ORG_PARAM}", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["claim"] == payload["claim"]
        assert data["status"] == "proposed"
        assert data["maturity_level"] >= 1
        assert uuid.UUID(data["id"])

    @pytest.mark.asyncio
    async def test_auto_advances_with_sources(self, client):
        """Should auto-advance to VALIDATED when sources are included."""
        payload = make_truth_payload(
            confidence=0.9,
            sources=[make_source_payload(), make_source_payload(source_url="https://example.com/doc2")],
        )
        resp = await client.post(f"/api/v1/truths{ORG_PARAM}", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "validated"
        assert len(data["sources"]) == 2

    @pytest.mark.asyncio
    async def test_stays_proposed_with_one_source(self, client):
        """Should stay PROPOSED when only 1 source is included."""
        payload = make_truth_payload(
            confidence=0.9,
            sources=[make_source_payload()],
        )
        resp = await client.post(f"/api/v1/truths{ORG_PARAM}", json=payload)

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "proposed"

    @pytest.mark.asyncio
    async def test_validation_error_on_empty_claim(self, client):
        """Should return 422 for an empty claim."""
        payload = make_truth_payload(claim="   ")
        resp = await client.post(f"/api/v1/truths{ORG_PARAM}", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_validation_error_on_confidence_out_of_range(self, client):
        """Should return 422 when confidence > 1.0."""
        payload = make_truth_payload(confidence=1.5)
        resp = await client.post(f"/api/v1/truths{ORG_PARAM}", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_creates_initial_validation_event(self, client):
        """Should create an initial PROPOSED ValidationEvent."""
        payload = make_truth_payload()
        resp = await client.post(f"/api/v1/truths{ORG_PARAM}", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        events = data["validation_events"]
        assert len(events) >= 1
        assert events[0]["to_status"] == "proposed"


# ---------------------------------------------------------------------------
# GET /api/v1/truths
# ---------------------------------------------------------------------------


class TestListTruths:
    @pytest.mark.asyncio
    async def test_lists_created_objects(self, client):
        """Should return created objects in the list."""
        # Create two objects
        for _ in range(2):
            await client.post(f"/api/v1/truths{ORG_PARAM}", json=make_truth_payload())

        resp = await client.get(f"/api/v1/truths{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_filters_by_status(self, client):
        """Should filter by status correctly."""
        # Create one object that stays PROPOSED (low confidence, no sources)
        await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(confidence=0.1),
        )

        resp = await client.get(f"/api/v1/truths{ORG_PARAM}&status=proposed")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["status"] == "proposed"

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        """Should respect limit and offset parameters."""
        for _ in range(3):
            await client.post(f"/api/v1/truths{ORG_PARAM}", json=make_truth_payload())

        resp = await client.get(f"/api/v1/truths{ORG_PARAM}&limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2


# ---------------------------------------------------------------------------
# GET /api/v1/truths/{id}
# ---------------------------------------------------------------------------


class TestGetTruth:
    @pytest.mark.asyncio
    async def test_returns_full_detail(self, client):
        """Should return full TruthObject with sources and events."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(sources=[make_source_payload()]),
        )
        truth_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/truths/{truth_id}{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == truth_id
        assert len(data["sources"]) >= 1
        assert len(data["validation_events"]) >= 1

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_id(self, client):
        """Should return 404 for a non-existent ID."""
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/truths/{fake_id}{ORG_PARAM}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Auth override in test client always returns TEST_ORG_ID; org isolation is covered by test_cross_tenant_hostile.py")
    async def test_org_isolation(self, client):
        """Should not return objects belonging to a different organization."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(),
        )
        truth_id = create_resp.json()["id"]

        other_org = uuid.uuid4()
        resp = await client.get(f"/api/v1/truths/{truth_id}?tenant_id={other_org}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/truths/{id}/validate
# ---------------------------------------------------------------------------


class TestValidateTruth:
    @pytest.mark.asyncio
    async def test_validate_flow(self, client):
        """Full flow: create with 2 sources → validated."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(
                confidence=0.9,
                sources=[
                    make_source_payload(),
                    make_source_payload(source_url="https://other.com/doc"),
                ],
            ),
        )
        assert create_resp.status_code == 201
        truth_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "validated"

    @pytest.mark.asyncio
    async def test_manual_validate_from_proposed(self, client, monkeypatch):
        """Manual validate action: PROPOSED → VALIDATED."""
        # Disable auto-advance so we can test manual validate
        from layer5_ground_truth import config
        from layer5_ground_truth.services import truth_service

        monkeypatch.setattr(config.get_settings(), "auto_advance_to_validated", False)
        monkeypatch.setattr(
            truth_service._state_machine._settings,
            "auto_advance_to_validated",
            False,
        )

        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(
                confidence=0.9,
                sources=[
                    make_source_payload(),
                    make_source_payload(source_url="https://other.com/doc"),
                ],
            ),
        )
        truth_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "proposed"

        validate_resp = await client.post(
            f"/api/v1/truths/{truth_id}/validate{ORG_PARAM}",
            json={
                "action": "validate",
                "actor": "reviewer@company.com",
                "actor_type": "human",
                "notes": "Verified against Q3 data",
            },
        )
        assert validate_resp.status_code == 200
        data = validate_resp.json()
        assert data["new_status"] == "validated"

    @pytest.mark.asyncio
    async def test_dispute_and_resolve(self, client):
        """Should dispute a truth object and then resolve it."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(
                confidence=0.9,
                sources=[
                    make_source_payload(),
                    make_source_payload(source_url="https://other.com"),
                ],
            ),
        )
        truth_id = create_resp.json()["id"]

        # Dispute
        dispute_resp = await client.post(
            f"/api/v1/truths/{truth_id}/validate{ORG_PARAM}",
            json={
                "action": "dispute",
                "actor": "analyst@company.com",
                "dispute_reason": "conflicting_sources",
                "notes": "Found contradicting data in Q4 report",
            },
        )
        assert dispute_resp.status_code == 200
        assert dispute_resp.json()["new_status"] == "disputed"

        # Resolve
        resolve_resp = await client.post(
            f"/api/v1/truths/{truth_id}/validate{ORG_PARAM}",
            json={
                "action": "resolve_dispute",
                "actor": "cfo@company.com",
                "notes": "Reviewed and confirmed original data is correct",
            },
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["new_status"] == "validated"

    @pytest.mark.asyncio
    async def test_reject_from_proposed(self, client):
        """Should reject a proposed truth object."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(confidence=0.1),
        )
        truth_id = create_resp.json()["id"]

        reject_resp = await client.post(
            f"/api/v1/truths/{truth_id}/validate{ORG_PARAM}",
            json={
                "action": "reject",
                "actor": "reviewer@company.com",
                "rejection_reason": "insufficient_evidence",
                "notes": "Not enough sources to validate",
            },
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["new_status"] == "rejected"

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_400(self, client):
        """Should return 400 for an invalid transition."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(confidence=0.1),
        )
        truth_id = create_resp.json()["id"]

        # Try to validate directly from PROPOSED without enough evidence
        resp = await client.post(
            f"/api/v1/truths/{truth_id}/validate{ORG_PARAM}",
            json={"action": "validate", "actor": "reviewer@company.com"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_dispute_requires_reason(self, client):
        """Should return 422 when dispute_reason is missing for dispute action."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(confidence=0.9, sources=[make_source_payload()]),
        )
        truth_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/truths/{truth_id}/validate{ORG_PARAM}",
            json={"action": "dispute", "actor": "analyst@company.com"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reject_requires_reason(self, client):
        """Should return 422 when rejection_reason is missing for reject action."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(confidence=0.1),
        )
        truth_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/truths/{truth_id}/validate{ORG_PARAM}",
            json={"action": "reject", "actor": "reviewer@company.com"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/truths/{id}/sources
# ---------------------------------------------------------------------------


class TestAddSource:
    @pytest.mark.asyncio
    async def test_adds_source_and_auto_advances(self, client):
        """Adding a source should trigger auto-advance to VALIDATED when threshold met."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(confidence=0.9),  # no sources initially
        )
        truth_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "proposed"

        source_resp = await client.post(
            f"/api/v1/truths/{truth_id}/sources{ORG_PARAM}",
            json=make_source_payload(),
        )
        assert source_resp.status_code == 201
        assert uuid.UUID(source_resp.json()["id"])

        # Still PROPOSED with only 1 source
        get_resp = await client.get(f"/api/v1/truths/{truth_id}{ORG_PARAM}")
        assert get_resp.json()["status"] == "proposed"

        # Add second source → auto-advance to VALIDATED
        source_resp2 = await client.post(
            f"/api/v1/truths/{truth_id}/sources{ORG_PARAM}",
            json=make_source_payload(source_url="https://other.com/doc"),
        )
        assert source_resp2.status_code == 201

        get_resp2 = await client.get(f"/api/v1/truths/{truth_id}{ORG_PARAM}")
        assert get_resp2.json()["status"] == "validated"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_truth(self, client):
        """Should return 404 when adding source to non-existent truth."""
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/truths/{fake_id}/sources{ORG_PARAM}",
            json=make_source_payload(),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/truths/{id}/audit
# ---------------------------------------------------------------------------


class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_returns_all_events(self, client):
        """Audit trail should contain all state transition events."""
        # Create → add 2 sources (triggers auto-advance to VALIDATED)
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(
                confidence=0.9,
                sources=[
                    make_source_payload(),
                    make_source_payload(source_url="https://other.com"),
                ],
            ),
        )
        truth_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/truths/{truth_id}/audit{ORG_PARAM}")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 2  # initial PROPOSED + advance to VALIDATED

        statuses = [e["to_status"] for e in events]
        assert "proposed" in statuses
        assert "validated" in statuses

    @pytest.mark.asyncio
    async def test_events_are_ordered_chronologically(self, client):
        """Audit events should be in chronological order."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}",
            json=make_truth_payload(confidence=0.9, sources=[make_source_payload()]),
        )
        truth_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/truths/{truth_id}/audit{ORG_PARAM}")
        events = resp.json()
        timestamps = [e["created_at"] for e in events]
        assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# DELETE /api/v1/truths/{id}
# ---------------------------------------------------------------------------


class TestSoftDelete:
    @pytest.mark.asyncio
    async def test_soft_deletes_object(self, client):
        """Deleted object should no longer be accessible via GET."""
        create_resp = await client.post(
            f"/api/v1/truths{ORG_PARAM}", json=make_truth_payload()
        )
        truth_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/v1/truths/{truth_id}{ORG_PARAM}")
        assert delete_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/truths/{truth_id}{ORG_PARAM}")
        assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/maturity-ladder
# ---------------------------------------------------------------------------


class TestMaturityLadder:
    @pytest.mark.asyncio
    async def test_returns_six_levels(self, client):
        """Maturity ladder must have exactly 6 levels (0–5)."""
        resp = await client.get("/api/v1/maturity-ladder")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["levels"]) == 6
        levels = [lvl["level"] for lvl in data["levels"]]
        assert levels == [0, 1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        """Public health endpoint should return 200 with status ok."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert "version" in data
        assert "timestamp" in data


class TestContractShapes:
    @pytest.mark.asyncio
    async def test_sync_to_kg_required_fields(self, client):
        resp = await client.post(f"/api/v1/truths/sync-kg{ORG_PARAM}")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"synced", "failed", "total_pending"}
        assert isinstance(data["synced"], int)
        assert isinstance(data["failed"], int)
        assert isinstance(data["total_pending"], int)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="409 envelope tested in unit/test_truth_object_validation.py::test_concurrent_transition_raises_conflict_error")
    async def test_transition_conflict_error_envelope_shape(self, monkeypatch, engine):
        """409 envelope shape when two sessions race the same transition."""
        pass
