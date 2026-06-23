"""Tests for the v3.0 consent service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from layer1_ingestion.shared.consent_service import ConsentService, compute_consent_hash
from layer1_ingestion.shared.models import SourceConsentStatus


class TestConsentHash:
    def test_hash_is_deterministic(self) -> None:
        a = compute_consent_hash("t", "a", "notes", {"purpose": "ingest"})
        b = compute_consent_hash("t", "a", "notes", {"purpose": "ingest"})
        assert a == b

    def test_hash_changes_with_scope(self) -> None:
        a = compute_consent_hash("t", "a", "notes", {"purpose": "ingest"})
        b = compute_consent_hash("t", "a", "notes", {"purpose": "analyze"})
        assert a != b


class TestConsentService:
    def test_create_consent_and_grant(self, db) -> None:
        service = ConsentService(db)
        tenant_id = uuid4()
        account_id = "acc-1"
        user_id = uuid4()
        consent = service.create_consent(
            tenant_id=tenant_id,
            account_id=account_id,
            source_type="notes",
            scope={"purpose": "ingest"},
            granted_by=user_id,
        )
        assert consent.status == SourceConsentStatus.PENDING.value
        granted = service.grant_consent(consent.id, user_id)
        assert granted.status == SourceConsentStatus.GRANTED.value
        assert granted.granted_by == user_id

    def test_active_consent_found_after_grant(self, db) -> None:
        service = ConsentService(db)
        tenant_id = uuid4()
        user_id = uuid4()
        consent = service.create_consent(
            tenant_id=tenant_id,
            account_id="acc-1",
            source_type="notes",
            scope={"purpose": "ingest"},
            granted_by=user_id,
        )
        service.grant_consent(consent.id, user_id)
        db.commit()
        active = service.get_active_consent(
            tenant_id=tenant_id,
            account_id="acc-1",
            source_type="notes",
            scope={"purpose": "ingest"},
        )
        assert active is not None
        assert active.id == consent.id

    def test_active_consent_not_found_when_expired(self, db) -> None:
        service = ConsentService(db)
        tenant_id = uuid4()
        user_id = uuid4()
        consent = service.create_consent(
            tenant_id=tenant_id,
            account_id="acc-1",
            source_type="notes",
            scope={"purpose": "ingest"},
            granted_by=user_id,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        service.grant_consent(consent.id, user_id)
        db.commit()
        active = service.get_active_consent(
            tenant_id=tenant_id,
            account_id="acc-1",
            source_type="notes",
            scope={"purpose": "ingest"},
        )
        assert active is None

    def test_require_active_consent_raises_when_missing(self, db) -> None:
        service = ConsentService(db)
        with pytest.raises(ValueError):
            service.require_active_consent(
                tenant_id=uuid4(),
                account_id="acc-1",
                source_type="notes",
                scope={"purpose": "ingest"},
            )

    def test_revoke_consent(self, db) -> None:
        service = ConsentService(db)
        tenant_id = uuid4()
        user_id = uuid4()
        consent = service.create_consent(
            tenant_id=tenant_id,
            account_id="acc-1",
            source_type="notes",
            scope={"purpose": "ingest"},
            granted_by=user_id,
        )
        service.grant_consent(consent.id, user_id)
        revoked = service.revoke_consent(consent.id, user_id)
        assert revoked.status == SourceConsentStatus.REVOKED.value
        assert revoked.revoked_at is not None
