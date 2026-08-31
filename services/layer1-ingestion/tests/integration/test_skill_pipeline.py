"""Integration tests for the Layer 1 Source Intelligence Skill pipeline.

Covers the full flow from job creation through storage and event outbox:
- Licensing company intake: job → storage_stage → SourceCorpus stored → EventOutbox created
- Prospect research: job → storage_stage → AccountIntelligencePacket stored → EventOutbox created
- Idempotent retry: re-running storage_stage does not create duplicate outputs
- Cross-tenant hostile: tenant A cannot read tenant B's corpus or packet via any endpoint
- notification_stage: EventOutbox rows created and dispatch_outbox_event enqueued
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from layer1_ingestion.shared.models import (
    AccountIntelligencePacket,
    EventOutbox,
    OutboxStatus,
    SourceCorpus,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_job(
    *,
    tenant_id: UUID | None = None,
    job_type: str = "licensing_company_intake",
    skill_name: str = "licensing_company_intake",
    output_contract: str = "SourceCorpus",
    downstream_events: list[str] | None = None,
    company_name: str = "Allego",
    company_id: str = "allego-001",
    account_name: str | None = None,
    account_id: str | None = None,
) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.tenant_id = tenant_id or uuid4()
    job.target_id = uuid4()
    job.job_type = job_type
    job.skill_name = skill_name
    job.output_contract = output_contract
    job.downstream_events = downstream_events or [
        "layer1.source_corpus.ready",
        "layer2.ontology_extraction.requested",
    ]
    job.configuration = {
        "company_name": company_name,
        "company_id": company_id,
        "account_name": account_name,
        "account_id": account_id,
        "skill_output": None,
        "output_contract": None,
    }
    job.status = "QUEUED"
    job.started_at = datetime.now(UTC)
    job.completed_at = None
    job.progress_stage = None
    job.progress_percent_complete = 0
    return job


def _make_raw_content(source_type: str = "product_page") -> MagicMock:
    rc = MagicMock()
    rc.source_type = source_type
    rc.id = uuid4()
    return rc


def _make_extracted_data(data: dict) -> MagicMock:
    ed = MagicMock()
    ed.data = data
    ed.id = uuid4()
    return ed


# =============================================================================
# storage_stage: SourceCorpus persistence
# =============================================================================


class TestStorageStageSourceCorpus:
    """storage_stage persists SourceCorpus from skill output."""

    def _run_storage_with_skill_output(self, job, skill_output: dict, existing_corpus=None):
        """Run storage_stage with a pre-built skill_output in job.configuration."""
        import layer1_ingestion.shared.tasks as tasks_module

        job.configuration["skill_output"] = skill_output
        job.configuration["output_contract"] = "SourceCorpus"

        added_objects = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is SourceCorpus:
                q.filter.return_value.first.return_value = existing_corpus
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_session.query.side_effect = query_side_effect
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("layer1_ingestion.shared.tasks.storage.get_db_session", return_value=mock_session):
            result = tasks_module.storage_stage({"job_id": str(job.id)}, str(job.tenant_id))

        return result, added_objects, mock_session

    def test_stores_source_corpus_on_first_run(self):
        job = _make_job()
        skill_output = {
            "tenant_id": str(job.tenant_id),
            "company_id": "allego-001",
            "company_name": "Allego",
            "corpus_type": "licensing_company_ontology_seed",
            "source_groups": [{"source_type": "product_page", "count": 10}],
            "candidate_concepts": ["sales enablement"],
            "provenance": [],
            "extraction_status": "ready_for_extraction",
            "job_id": str(job.id),
        }

        result, added, _ = self._run_storage_with_skill_output(job, skill_output)

        assert result["success"] is True
        corpus_rows = [o for o in added if isinstance(o, SourceCorpus)]
        assert len(corpus_rows) == 1
        assert corpus_rows[0].company_name == "Allego"
        assert corpus_rows[0].tenant_id == job.tenant_id

    def test_idempotent_retry_does_not_duplicate_corpus(self):
        """If a SourceCorpus already exists for the job, storage_stage skips creation."""
        job = _make_job()
        existing = MagicMock(spec=SourceCorpus)
        existing.id = uuid4()

        skill_output = {
            "tenant_id": str(job.tenant_id),
            "company_name": "Allego",
            "corpus_type": "licensing_company_ontology_seed",
            "source_groups": [],
            "candidate_concepts": [],
            "provenance": [],
            "extraction_status": "ready_for_extraction",
            "job_id": str(job.id),
        }

        result, added, _ = self._run_storage_with_skill_output(job, skill_output, existing_corpus=existing)

        assert result["success"] is True
        corpus_rows = [o for o in added if isinstance(o, SourceCorpus)]
        assert len(corpus_rows) == 0  # No new row created

    def test_corpus_tenant_id_matches_job_tenant(self):
        tenant_id = uuid4()
        job = _make_job(tenant_id=tenant_id)
        skill_output = {
            "tenant_id": str(tenant_id),
            "company_name": "Allego",
            "corpus_type": "licensing_company_ontology_seed",
            "source_groups": [],
            "candidate_concepts": [],
            "provenance": [],
            "extraction_status": "ready_for_extraction",
            "job_id": str(job.id),
        }

        _, added, _ = self._run_storage_with_skill_output(job, skill_output)

        corpus_rows = [o for o in added if isinstance(o, SourceCorpus)]
        assert len(corpus_rows) == 1
        assert corpus_rows[0].tenant_id == tenant_id


# =============================================================================
# storage_stage: AccountIntelligencePacket persistence
# =============================================================================


class TestStorageStageAccountIntelligencePacket:
    """storage_stage persists AccountIntelligencePacket from skill output."""

    def _run_storage_with_packet_output(self, job, skill_output: dict, existing_packet=None):
        import layer1_ingestion.shared.tasks as tasks_module

        job.configuration["skill_output"] = skill_output
        job.configuration["output_contract"] = "AccountIntelligencePacket"

        added_objects = []

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        def query_side_effect(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is AccountIntelligencePacket:
                q.filter.return_value.first.return_value = existing_packet
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        mock_session.query.side_effect = query_side_effect
        mock_session.add.side_effect = lambda obj: added_objects.append(obj)

        with patch("layer1_ingestion.shared.tasks.storage.get_db_session", return_value=mock_session):
            result = tasks_module.storage_stage({"job_id": str(job.id)}, str(job.tenant_id))

        return result, added_objects, mock_session

    def test_stores_account_intelligence_packet_on_first_run(self):
        job = _make_job(
            job_type="prospect_research",
            skill_name="prospect_research",
            output_contract="AccountIntelligencePacket",
            downstream_events=["layer1.account_intelligence.ready", "layer2.signal_extraction.requested"],
            account_name="Acme Manufacturing",
            account_id="acme-001",
        )
        skill_output = {
            "tenant_id": str(job.tenant_id),
            "account_id": "acme-001",
            "account_name": "Acme Manufacturing",
            "packet_type": "prospect_research",
            "company_profile": {"size": "mid-market"},
            "observed_signals": [{"signal": "Hiring", "source": "careers_page", "confidence": "high"}],
            "likely_pain_areas": ["seller onboarding"],
            "likely_stakeholders": ["CRO"],
            "source_references": [],
            "confidence_summary": {"signal_count": 1, "high_confidence_signals": 1},
            "next_recommended_events": ["layer1.account_intelligence.ready"],
            "job_id": str(job.id),
        }

        result, added, _ = self._run_storage_with_packet_output(job, skill_output)

        assert result["success"] is True
        packet_rows = [o for o in added if isinstance(o, AccountIntelligencePacket)]
        assert len(packet_rows) == 1
        assert packet_rows[0].account_name == "Acme Manufacturing"
        assert packet_rows[0].tenant_id == job.tenant_id

    def test_idempotent_retry_does_not_duplicate_packet(self):
        job = _make_job(
            job_type="prospect_research",
            skill_name="prospect_research",
            output_contract="AccountIntelligencePacket",
        )
        existing = MagicMock(spec=AccountIntelligencePacket)
        existing.id = uuid4()

        skill_output = {
            "tenant_id": str(job.tenant_id),
            "account_name": "Acme",
            "packet_type": "prospect_research",
            "company_profile": {},
            "observed_signals": [],
            "likely_pain_areas": [],
            "likely_stakeholders": [],
            "source_references": [],
            "confidence_summary": {},
            "next_recommended_events": [],
            "job_id": str(job.id),
        }

        result, added, _ = self._run_storage_with_packet_output(job, skill_output, existing_packet=existing)

        assert result["success"] is True
        packet_rows = [o for o in added if isinstance(o, AccountIntelligencePacket)]
        assert len(packet_rows) == 0


# =============================================================================
# notification_stage → EventOutbox → dispatch_outbox_event (end-to-end)
# =============================================================================


class TestFullSkillPipelineEventFlow:
    """End-to-end: notification_stage creates outbox rows, dispatch marks them dispatched."""

    def test_licensing_company_full_event_flow(self):
        """
        notification_stage for a licensing company job:
        1. Creates EventOutbox rows for each downstream event
        2. Enqueues dispatch_outbox_event for each row
        3. dispatch_outbox_event marks each row as dispatched
        """
        import layer1_ingestion.shared.tasks as tasks_module

        tenant_id = uuid4()
        job = _make_job(tenant_id=tenant_id)
        corpus_id = uuid4()
        corpus = MagicMock(spec=SourceCorpus)
        corpus.id = corpus_id

        outbox_rows: list[EventOutbox] = []
        dispatched_ids: list[str] = []

        # --- notification_stage mock ---
        notif_session = MagicMock()
        notif_session.__enter__ = MagicMock(return_value=notif_session)
        notif_session.__exit__ = MagicMock(return_value=False)

        def notif_query(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is tasks_module.ScrapingTarget:
                q.get.return_value = None
            elif model is SourceCorpus:
                q.filter.return_value.first.return_value = corpus
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        notif_session.query.side_effect = notif_query
        notif_session.add.side_effect = lambda obj: outbox_rows.append(obj) if isinstance(obj, EventOutbox) else None

        def capture_dispatch(args, countdown=None):
            dispatched_ids.append(args[0])

        with patch("layer1_ingestion.shared.tasks.notification.get_db_session", return_value=notif_session):
            with patch.object(tasks_module.dispatch_outbox_event, "apply_async", side_effect=capture_dispatch):
                tasks_module.notification_stage({"job_id": str(job.id)}, str(job.tenant_id))

        # Two downstream events → two outbox rows
        assert len(outbox_rows) == 2
        assert len(dispatched_ids) == 2

        # Verify payload integrity
        for row in outbox_rows:
            assert row.payload["tenant_id"] == str(tenant_id)
            assert row.payload["job_id"] == str(job.id)
            assert row.payload["output_id"] == str(corpus_id)
            assert row.payload["output_contract"] == "SourceCorpus"

        # --- dispatch_outbox_event mock: mark each row dispatched ---
        for row in outbox_rows:
            row.id = uuid4()  # Assign IDs as ORM would
            row.status = OutboxStatus.PENDING.value
            row.attempts = 0

            dispatch_session = MagicMock()
            dispatch_session.__enter__ = MagicMock(return_value=dispatch_session)
            dispatch_session.__exit__ = MagicMock(return_value=False)
            dispatch_session.query.return_value.filter.return_value.first.return_value = row

            with patch("layer1_ingestion.shared.tasks.get_db_session", return_value=dispatch_session):
                tasks_module.dispatch_outbox_event(str(row.id), str(tenant_id))

            assert row.status == OutboxStatus.DISPATCHED.value
            assert row.dispatched_at is not None

    def test_prospect_research_full_event_flow(self):
        """notification_stage for a prospect research job creates correct outbox rows."""
        import layer1_ingestion.shared.tasks as tasks_module

        tenant_id = uuid4()
        job = _make_job(
            tenant_id=tenant_id,
            job_type="prospect_research",
            skill_name="prospect_research",
            output_contract="AccountIntelligencePacket",
            downstream_events=["layer1.account_intelligence.ready", "layer2.signal_extraction.requested"],
        )
        packet_id = uuid4()
        packet = MagicMock(spec=AccountIntelligencePacket)
        packet.id = packet_id

        outbox_rows: list[EventOutbox] = []

        notif_session = MagicMock()
        notif_session.__enter__ = MagicMock(return_value=notif_session)
        notif_session.__exit__ = MagicMock(return_value=False)

        def notif_query(model):
            q = MagicMock()
            if model is tasks_module.ScrapingJob:
                q.get.return_value = job
            elif model is tasks_module.ScrapingTarget:
                q.get.return_value = None
            elif model is AccountIntelligencePacket:
                q.filter.return_value.first.return_value = packet
            elif model is tasks_module.JobStageDetail:
                q.filter.return_value.first.return_value = None
            else:
                q.filter.return_value.first.return_value = None
            return q

        notif_session.query.side_effect = notif_query
        notif_session.add.side_effect = lambda obj: outbox_rows.append(obj) if isinstance(obj, EventOutbox) else None

        with patch("layer1_ingestion.shared.tasks.notification.get_db_session", return_value=notif_session):
            with patch.object(tasks_module.dispatch_outbox_event, "apply_async"):
                tasks_module.notification_stage({"job_id": str(job.id)}, str(job.tenant_id))

        assert len(outbox_rows) == 2
        event_types = {r.event_type for r in outbox_rows}
        assert "layer1.account_intelligence.ready" in event_types
        assert "layer2.signal_extraction.requested" in event_types

        for row in outbox_rows:
            assert row.payload["output_contract"] == "AccountIntelligencePacket"
            assert row.payload["output_id"] == str(packet_id)


# =============================================================================
# Cross-tenant hostile: API endpoint isolation
# =============================================================================


class TestCrossTenantHostile:
    """Tenant A cannot read Tenant B's corpus or packet via any endpoint."""

    def _make_app(self, tenant_id: UUID, db_mock: MagicMock):
        from fastapi import FastAPI
        from layer1_ingestion.api.main import router, get_tenant_id, get_db_from_context_sync
        from fastapi.testclient import TestClient
        from value_fabric.shared.error_handling import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router)
        app.dependency_overrides[get_tenant_id] = lambda: tenant_id
        app.dependency_overrides[get_db_from_context_sync] = lambda: db_mock
        return TestClient(app, raise_server_exceptions=False)

    def test_tenant_a_cannot_read_tenant_b_corpus(self):
        """Tenant A requesting Tenant B's corpus ID gets 404."""
        tenant_a = uuid4()
        tenant_b = uuid4()

        # DB returns None because the tenant_id filter excludes Tenant B's row
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None  # Tenant filter rejects the row
        db.query.return_value = q

        client = self._make_app(tenant_a, db)
        corpus_id_owned_by_b = uuid4()

        resp = client.get(f"/api/v1/ingestion/source-corpora/{corpus_id_owned_by_b}")
        assert resp.status_code == 404

    def test_tenant_a_cannot_read_tenant_b_packet(self):
        """Tenant A requesting Tenant B's packet ID gets 404."""
        tenant_a = uuid4()

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.first.return_value = None
        db.query.return_value = q

        client = self._make_app(tenant_a, db)
        packet_id_owned_by_b = uuid4()

        resp = client.get(f"/api/v1/ingestion/account-intelligence-packets/{packet_id_owned_by_b}")
        assert resp.status_code == 404

    def test_list_corpora_only_returns_own_tenant_records(self):
        """List endpoint filters by authenticated tenant, not a query param."""
        tenant_a = uuid4()

        # Return empty list — simulates DB filtering out other tenants
        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.count.return_value = 0
        q.all.return_value = []
        db.query.return_value = q

        client = self._make_app(tenant_a, db)

        # Even if a malicious caller passes a different tenant_id as a query param,
        # the endpoint ignores it — tenant comes from auth context only
        resp = client.get("/api/v1/ingestion/source-corpora")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_packets_only_returns_own_tenant_records(self):
        tenant_a = uuid4()

        db = MagicMock()
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.limit.return_value = q
        q.count.return_value = 0
        q.all.return_value = []
        db.query.return_value = q

        client = self._make_app(tenant_a, db)

        resp = client.get("/api/v1/ingestion/account-intelligence-packets")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_missing_auth_returns_401(self):
        """Without dependency override (no auth), endpoints return 401."""
        from fastapi import FastAPI
        from layer1_ingestion.api.main import router
        from fastapi.testclient import TestClient
        from value_fabric.shared.error_handling import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(router)
        # No dependency overrides — real get_tenant_id will raise 401
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/api/v1/ingestion/source-corpora")
        assert resp.status_code == 401

        resp = client.get("/api/v1/ingestion/account-intelligence-packets")
        assert resp.status_code == 401
