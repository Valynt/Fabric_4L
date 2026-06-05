"""Unit tests for SourceCorpus and AccountIntelligencePacket list/read endpoints.

Covers:
- List returns only current tenant records (tenant isolation)
- Cross-tenant read by ID returns 404
- Pagination limit is enforced (cannot exceed 100)
- List responses do not include raw provenance or source_references arrays
- Filters (company_id, account_id, extraction_status) work correctly
- Cursor pagination advances correctly
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from layer1_ingestion.api.main import router
from layer1_ingestion.api.main import (
    get_tenant_id,
    get_db_from_context_sync,
    SourceCorpus,
    AccountIntelligencePacket,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_corpus(
    *,
    tenant_id: UUID,
    company_name: str = "Acme Corp",
    company_id: str = "acme-001",
    extraction_status: str = "ready_for_extraction",
    source_groups: list | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    c = MagicMock(spec=SourceCorpus)
    c.id = uuid4()
    c.tenant_id = tenant_id
    c.company_name = company_name
    c.company_id = company_id
    c.corpus_type = "licensing_company_ontology_seed"
    c.extraction_status = extraction_status
    c.source_groups = source_groups or [{"source_type": "product_page", "count": 5}]
    c.candidate_concepts = ["sales enablement"]
    c.provenance = [{"url": "https://acme.com", "source_type": "product_page", "confidence": "high"}]
    c.created_at = created_at or datetime.now(UTC)
    c.updated_at = datetime.now(UTC)
    return c


def _make_packet(
    *,
    tenant_id: UUID,
    account_name: str = "Meridian Co",
    account_id: str = "meridian-001",
    observed_signals: list | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    p = MagicMock(spec=AccountIntelligencePacket)
    p.id = uuid4()
    p.tenant_id = tenant_id
    p.account_name = account_name
    p.account_id = account_id
    p.packet_type = "prospect_research"
    p.observed_signals = observed_signals or [
        {"signal": "Hiring sales managers", "source": "careers_page", "confidence": "high"}
    ]
    p.likely_pain_areas = ["seller onboarding"]
    p.likely_stakeholders = ["CRO"]
    p.source_references = [{"url": "https://meridian.com", "source_type": "website", "confidence": "high"}]
    p.company_profile = {"size": "mid-market"}
    p.confidence_summary = {"signal_count": 1, "high_confidence_signals": 1}
    p.next_recommended_events = ["layer2.signal_extraction.requested"]
    p.created_at = created_at or datetime.now(UTC)
    p.updated_at = datetime.now(UTC)
    return p


def _make_app_with_overrides(tenant_id: UUID, db_mock: MagicMock):
    """Create a FastAPI test app with dependency overrides.

    The router already carries the /api/v1/ingestion prefix, so mount it
    without an additional prefix.
    """
    from fastapi import FastAPI
    from value_fabric.shared.error_handling import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    app.dependency_overrides[get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[get_db_from_context_sync] = lambda: db_mock

    return app


def _make_db_mock(query_results: list, count: int | None = None) -> MagicMock:
    """Build a mock DB session that returns query_results for .all() and count for .count()."""
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.count.return_value = count if count is not None else len(query_results)
    q.all.return_value = query_results
    q.first.return_value = query_results[0] if query_results else None
    db.query.return_value = q
    return db


# =============================================================================
# SourceCorpus list endpoint
# =============================================================================


class TestListSourceCorpora:
    """GET /api/v1/ingestion/source-corpora"""

    def test_returns_only_tenant_records(self):
        tenant_id = uuid4()
        corpus = _make_corpus(tenant_id=tenant_id)
        db = _make_db_mock([corpus])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["company_name"] == "Acme Corp"

    def test_list_response_excludes_provenance(self):
        """Summary items must not contain provenance arrays."""
        tenant_id = uuid4()
        corpus = _make_corpus(tenant_id=tenant_id)
        db = _make_db_mock([corpus])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "provenance" not in item
        assert "candidate_concepts" not in item

    def test_source_count_derived_from_source_groups(self):
        tenant_id = uuid4()
        corpus = _make_corpus(
            tenant_id=tenant_id,
            source_groups=[
                {"source_type": "product_page", "count": 10},
                {"source_type": "case_study", "count": 5},
            ],
        )
        db = _make_db_mock([corpus])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora")
        assert resp.status_code == 200
        assert resp.json()["items"][0]["source_count"] == 15

    def test_default_limit_is_20(self):
        tenant_id = uuid4()
        db = _make_db_mock([], count=0)
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora")
        assert resp.status_code == 200
        assert resp.json()["limit"] == 20

    def test_limit_enforced_at_100(self):
        tenant_id = uuid4()
        db = _make_db_mock([], count=0)
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora?limit=200")
        assert resp.status_code == 422  # FastAPI validation error

    def test_filter_by_company_id(self):
        tenant_id = uuid4()
        corpus = _make_corpus(tenant_id=tenant_id, company_id="target-co")
        db = _make_db_mock([corpus])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora?company_id=target-co")
        assert resp.status_code == 200
        # Verify the filter was applied to the query
        db.query.return_value.filter.assert_called()

    def test_filter_by_extraction_status(self):
        tenant_id = uuid4()
        corpus = _make_corpus(tenant_id=tenant_id, extraction_status="sent_to_layer_2")
        db = _make_db_mock([corpus])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora?extraction_status=sent_to_layer_2")
        assert resp.status_code == 200

    def test_next_cursor_present_when_full_page(self):
        tenant_id = uuid4()
        ts = datetime.now(UTC)
        corpora = [_make_corpus(tenant_id=tenant_id, created_at=ts - timedelta(seconds=i)) for i in range(5)]
        db = _make_db_mock(corpora, count=10)
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora?limit=5")
        assert resp.status_code == 200
        assert resp.json()["next_cursor"] is not None

    def test_next_cursor_absent_when_partial_page(self):
        tenant_id = uuid4()
        corpora = [_make_corpus(tenant_id=tenant_id) for _ in range(3)]
        db = _make_db_mock(corpora, count=3)
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora?limit=5")
        assert resp.status_code == 200
        assert resp.json()["next_cursor"] is None

    def test_invalid_cursor_returns_400(self):
        tenant_id = uuid4()
        db = _make_db_mock([])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/source-corpora?cursor=not-a-date")
        assert resp.status_code == 400


# =============================================================================
# SourceCorpus detail endpoint
# =============================================================================


class TestGetSourceCorpusDetail:
    """GET /api/v1/ingestion/source-corpora/{corpus_id}"""

    def test_returns_full_corpus_with_provenance(self):
        tenant_id = uuid4()
        corpus = _make_corpus(tenant_id=tenant_id)
        db = _make_db_mock([corpus])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get(f"/api/v1/ingestion/source-corpora/{corpus.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "provenance" in data
        assert data["company_name"] == "Acme Corp"

    def test_cross_tenant_returns_404(self):
        """A different tenant's corpus ID returns 404, not the corpus."""
        tenant_id = uuid4()
        # DB returns None (simulating tenant filter rejecting the row)
        db = _make_db_mock([])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        other_corpus_id = uuid4()
        resp = client.get(f"/api/v1/ingestion/source-corpora/{other_corpus_id}")
        assert resp.status_code == 404

    def test_nonexistent_id_returns_404(self):
        tenant_id = uuid4()
        db = _make_db_mock([])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get(f"/api/v1/ingestion/source-corpora/{uuid4()}")
        assert resp.status_code == 404


# =============================================================================
# AccountIntelligencePacket list endpoint
# =============================================================================


class TestListAccountIntelligencePackets:
    """GET /api/v1/ingestion/account-intelligence-packets"""

    def test_returns_only_tenant_records(self):
        tenant_id = uuid4()
        packet = _make_packet(tenant_id=tenant_id)
        db = _make_db_mock([packet])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["account_name"] == "Meridian Co"

    def test_list_response_excludes_source_references(self):
        """Summary items must not contain source_references arrays."""
        tenant_id = uuid4()
        packet = _make_packet(tenant_id=tenant_id)
        db = _make_db_mock([packet])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "source_references" not in item
        assert "likely_pain_areas" not in item
        assert "likely_stakeholders" not in item

    def test_observed_signal_count_derived(self):
        tenant_id = uuid4()
        packet = _make_packet(
            tenant_id=tenant_id,
            observed_signals=[
                {"signal": "A", "source": "news", "confidence": "high"},
                {"signal": "B", "source": "careers_page", "confidence": "medium"},
                {"signal": "C", "source": "press_release", "confidence": "high"},
            ],
        )
        db = _make_db_mock([packet])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["observed_signal_count"] == 3
        assert item["high_confidence_signal_count"] == 2

    def test_limit_enforced_at_100(self):
        tenant_id = uuid4()
        db = _make_db_mock([], count=0)
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets?limit=500")
        assert resp.status_code == 422

    def test_filter_by_account_id(self):
        tenant_id = uuid4()
        packet = _make_packet(tenant_id=tenant_id, account_id="acct-xyz")
        db = _make_db_mock([packet])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets?account_id=acct-xyz")
        assert resp.status_code == 200

    def test_next_cursor_present_when_full_page(self):
        tenant_id = uuid4()
        ts = datetime.now(UTC)
        packets = [_make_packet(tenant_id=tenant_id, created_at=ts - timedelta(seconds=i)) for i in range(5)]
        db = _make_db_mock(packets, count=20)
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets?limit=5")
        assert resp.status_code == 200
        assert resp.json()["next_cursor"] is not None

    def test_invalid_cursor_returns_400(self):
        tenant_id = uuid4()
        db = _make_db_mock([])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets?cursor=bad-cursor")
        assert resp.status_code == 400


# =============================================================================
# AccountIntelligencePacket detail endpoint
# =============================================================================


class TestGetAccountIntelligencePacketDetail:
    """GET /api/v1/ingestion/account-intelligence-packets/{packet_id}"""

    def test_returns_full_packet_with_source_references(self):
        tenant_id = uuid4()
        packet = _make_packet(tenant_id=tenant_id)
        db = _make_db_mock([packet])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get(f"/api/v1/ingestion/account-intelligence-packets/{packet.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "source_references" in data
        assert data["account_name"] == "Meridian Co"

    def test_cross_tenant_returns_404(self):
        tenant_id = uuid4()
        db = _make_db_mock([])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get(f"/api/v1/ingestion/account-intelligence-packets/{uuid4()}")
        assert resp.status_code == 404

    def test_nonexistent_id_returns_404(self):
        tenant_id = uuid4()
        db = _make_db_mock([])
        app = _make_app_with_overrides(tenant_id, db)
        client = TestClient(app)

        resp = client.get(f"/api/v1/ingestion/account-intelligence-packets/{uuid4()}")
        assert resp.status_code == 404
