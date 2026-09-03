"""Tests for audit models and emitter (shared/audit/)."""

import json
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ..emitter import AuditEmitter, _scrub_details, emit_audit_event
from ..models import AuditAction, AuditEvent, AuditOutcome


# ═══════════════════════════════════════════════════════════════════════════
# Audit models
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditAction:
    def test_is_string_enum(self):
        assert isinstance(AuditAction.USER_LOGIN, str)
        assert AuditAction.USER_LOGIN == "user.login"

    def test_all_unique(self):
        values = [a.value for a in AuditAction]
        assert len(values) == len(set(values))

    def test_dot_namespaced(self):
        """Every action uses dot-namespaced format."""
        for a in AuditAction:
            assert "." in a.value, f"{a.name} missing dot namespace"


class TestAuditOutcome:
    def test_values(self):
        assert AuditOutcome.SUCCESS == "success"
        assert AuditOutcome.FAILURE == "failure"
        assert AuditOutcome.PARTIAL == "partial"


class TestAuditEvent:
    def test_default_creation(self):
        event = AuditEvent(action=AuditAction.USER_LOGIN)
        assert isinstance(event.id, UUID)
        assert event.tenant_id is None
        assert event.outcome == "success"  # use_enum_values
        assert isinstance(event.timestamp, datetime)
        assert event.details == {}

    def test_full_creation(self):
        tenant = uuid4()
        event = AuditEvent(
            action=AuditAction.TENANT_CREATED,
            tenant_id=tenant,
            user_id="admin-1",
            api_key_id="key-5",
            resource_type="Tenant",
            resource_id=str(tenant),
            ip_address="192.168.1.1",
            user_agent="Test/1.0",
            request_id="req_abc",
            outcome=AuditOutcome.SUCCESS,
            details={"plan": "enterprise"},
        )
        assert event.tenant_id == tenant
        assert event.user_id == "admin-1"
        assert event.details["plan"] == "enterprise"

    def test_timestamp_is_utc(self):
        event = AuditEvent(action=AuditAction.USER_LOGIN)
        assert event.timestamp.tzinfo is not None


# ═══════════════════════════════════════════════════════════════════════════
# Scrub details
# ═══════════════════════════════════════════════════════════════════════════


class TestScrubDetails:
    def test_redacts_password(self):
        result = _scrub_details({"password": "secret123", "name": "Alice"})
        assert result["password"] == "[REDACTED]"
        assert result["name"] == "Alice"

    def test_redacts_token(self):
        result = _scrub_details({"token": "jwt.xyz", "action": "login"})
        assert result["token"] == "[REDACTED]"
        assert result["action"] == "login"

    def test_redacts_case_insensitive(self):
        result = _scrub_details({"Password": "x", "TOKEN": "y"})
        assert result["Password"] == "[REDACTED]"
        assert result["TOKEN"] == "[REDACTED]"

    def test_all_sensitive_keys_redacted(self):
        sensitive = {
            "password": "a",
            "hashed_password": "b",
            "secret": "c",
            "token": "d",
            "api_key": "e",
            "key_hash": "f",
            "access_token": "g",
            "refresh_token": "h",
            "private_key": "i",
            "client_secret": "j",
        }
        result = _scrub_details(sensitive)
        for v in result.values():
            assert v == "[REDACTED]"

    def test_empty_dict(self):
        assert _scrub_details({}) == {}

    def test_preserves_non_sensitive(self):
        result = _scrub_details({"user": "bob", "count": 42})
        assert result == {"user": "bob", "count": 42}


# ═══════════════════════════════════════════════════════════════════════════
# emit_audit_event
# ═══════════════════════════════════════════════════════════════════════════


class TestEmitAuditEvent:
    def test_returns_audit_event(self):
        event = emit_audit_event(AuditAction.USER_LOGIN)
        assert isinstance(event, AuditEvent)
        assert event.action == "user.login"

    def test_scrubs_details(self):
        event = emit_audit_event(
            AuditAction.API_KEY_CREATED,
            details={"api_key": "raw-secret", "name": "My Key"},
        )
        assert event.details["api_key"] == "[REDACTED]"
        assert event.details["name"] == "My Key"

    def test_logs_json(self, caplog):
        with caplog.at_level(logging.INFO, logger="vf.audit"):
            emit_audit_event(
                AuditAction.TENANT_CREATED,
                tenant_id=uuid4(),
                user_id="admin-1",
            )
        # Verify structured log output
        assert len(caplog.records) == 1
        log_data = json.loads(caplog.records[0].message)
        assert log_data["audit"] is True
        assert log_data["action"] == "tenant.created"
        assert log_data["user_id"] == "admin-1"

    def test_all_fields_passed_through(self):
        tenant = uuid4()
        event = emit_audit_event(
            AuditAction.DOCUMENT_INGESTED,
            tenant_id=tenant,
            user_id="user-1",
            api_key_id="key-1",
            resource_type="Document",
            resource_id="doc-42",
            ip_address="10.0.0.1",
            user_agent="Test/2.0",
            request_id="req_123",
            outcome=AuditOutcome.FAILURE,
        )
        assert event.tenant_id == tenant
        assert event.user_id == "user-1"
        assert event.resource_type == "Document"
        assert event.outcome == "failure"


# ═══════════════════════════════════════════════════════════════════════════
# AuditEmitter.write_to_db
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditEmitterWriteToDb:
    @pytest.mark.asyncio
    async def test_successful_write(self):
        """write_to_db executes SQL and commits."""
        event = AuditEvent(action=AuditAction.USER_LOGIN)
        mock_session = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await AuditEmitter.write_to_db(event, mock_factory)

        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_db_failure_logged_not_raised(self, caplog):
        """DB failure is logged but does not propagate."""
        event = AuditEvent(action=AuditAction.USER_LOGIN)

        async def failing_factory():
            raise ConnectionError("DB down")

        # Should not raise
        with caplog.at_level(logging.ERROR):
            await AuditEmitter.write_to_db(event, failing_factory)
        assert "Failed to persist audit event" in caplog.text
