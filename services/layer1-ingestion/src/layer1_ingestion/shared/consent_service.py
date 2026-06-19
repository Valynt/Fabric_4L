"""Consent service for canonical source ingestion.

v3.0 requires explicit consent before a source ingestion run can be created.
This module provides a lightweight service layer for creating, granting,
revoking, and validating consent records.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .models import SourceConsent, SourceConsentStatus


def compute_consent_hash(
    tenant_id: str,
    account_id: str,
    source_type: str,
    scope: dict[str, Any],
) -> str:
    """Deterministic hash of the consent grant scope.

    The hash is stable across retries so the same consent scope can be
    referenced by ingestion runs without creating duplicate records.
    """
    canonical_scope = sorted(
        ((k, str(v)) for k, v in scope.items()),
        key=lambda item: item[0],
    )
    parts = [tenant_id, account_id, source_type, str(canonical_scope)]
    key = "|".join(parts)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class ConsentService:
    """Service for managing source ingestion consent records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active_consent(
        self,
        tenant_id: UUID,
        account_id: str,
        source_type: str,
        scope: dict[str, Any],
    ) -> SourceConsent | None:
        """Return a granted, non-expired consent record for the scope if one exists."""
        consent_hash = compute_consent_hash(str(tenant_id), account_id, source_type, scope)
        return (
            self._db.query(SourceConsent)
            .filter(
                SourceConsent.tenant_id == tenant_id,
                SourceConsent.account_id == account_id,
                SourceConsent.source_type == source_type,
                SourceConsent.consent_hash == consent_hash,
                SourceConsent.status == SourceConsentStatus.GRANTED.value,
            )
            .filter(
                SourceConsent.expires_at.is_(None)
                | (SourceConsent.expires_at > datetime.now(UTC))
            )
            .first()
        )

    def create_consent(
        self,
        tenant_id: UUID,
        account_id: str,
        source_type: str,
        scope: dict[str, Any],
        *,
        granted_by: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> SourceConsent:
        """Create a pending consent record for a source ingestion scope.

        Idempotent: if a pending/consent_hash identical record exists, it is returned.
        """
        consent_hash = compute_consent_hash(str(tenant_id), account_id, source_type, scope)
        existing = (
            self._db.query(SourceConsent)
            .filter(
                SourceConsent.tenant_id == tenant_id,
                SourceConsent.account_id == account_id,
                SourceConsent.source_type == source_type,
                SourceConsent.consent_hash == consent_hash,
            )
            .first()
        )
        if existing:
            return existing

        consent = SourceConsent(
            tenant_id=tenant_id,
            account_id=account_id,
            source_type=source_type,
            scope=scope,
            consent_hash=consent_hash,
            status=SourceConsentStatus.PENDING.value,
            granted_by=granted_by,
            expires_at=expires_at,
        )
        self._db.add(consent)
        self._db.flush()
        return consent

    def grant_consent(
        self,
        consent_id: UUID,
        granted_by: UUID,
        *,
        expires_at: datetime | None = None,
    ) -> SourceConsent:
        """Mark a consent record as granted."""
        consent = (
            self._db.query(SourceConsent)
            .filter(SourceConsent.id == consent_id)
            .first()
        )
        if not consent:
            raise ValueError(f"Consent {consent_id} not found")
        consent.status = SourceConsentStatus.GRANTED.value  # type: ignore[assignment]
        consent.granted_by = granted_by
        consent.granted_at = datetime.now(UTC)
        if expires_at:
            consent.expires_at = expires_at
        return consent

    def revoke_consent(
        self,
        consent_id: UUID,
        revoked_by: UUID,
    ) -> SourceConsent:
        """Revoke a consent record."""
        consent = (
            self._db.query(SourceConsent)
            .filter(SourceConsent.id == consent_id)
            .first()
        )
        if not consent:
            raise ValueError(f"Consent {consent_id} not found")
        consent.status = SourceConsentStatus.REVOKED.value  # type: ignore[assignment]
        consent.revoked_at = datetime.now(UTC)
        return consent

    def require_active_consent(
        self,
        tenant_id: UUID,
        account_id: str,
        source_type: str,
        scope: dict[str, Any],
    ) -> SourceConsent:
        """Return an active consent record or raise.

        Used by source intake to enforce the v3.0 consent-before-ingestion rule.
        """
        consent = self.get_active_consent(tenant_id, account_id, source_type, scope)
        if not consent:
            raise ValueError(
                f"Active consent is required for source_type={source_type} account={account_id}"
            )
        return consent
