from __future__ import annotations

"""
Unit tests for Neo4jValuePackService._increment_version and BusinessCaseService.

Tests the pure-Python helpers that require no external dependencies.
"""


from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Neo4jValuePackService._increment_version
# ──────────────────────────────────────────────────────────────────────────────

class TestIncrementVersion:
    """Tests for the version increment helper."""

    def _svc(self):
        from layer4_agents.services.value_pack_service import Neo4jValuePackService

        driver = MagicMock()
        return Neo4jValuePackService(driver=driver)

    @pytest.mark.unit
    def test_increment_patch(self):
        svc = self._svc()
        assert svc._increment_version("1.0.0") == "1.0.1"
        assert svc._increment_version("2.3.7") == "2.3.8"

    @pytest.mark.unit
    def test_increment_from_zero(self):
        svc = self._svc()
        assert svc._increment_version("0.0.0") == "0.0.1"

    @pytest.mark.unit
    def test_increment_large_patch(self):
        svc = self._svc()
        assert svc._increment_version("1.0.99") == "1.0.100"

    @pytest.mark.unit
    def test_increment_preserves_major_minor(self):
        svc = self._svc()
        result = svc._increment_version("3.5.2")
        major, minor, patch = result.split(".")
        assert major == "3"
        assert minor == "5"
        assert patch == "3"

    @pytest.mark.unit
    def test_invalid_version_falls_back(self):
        """Malformed version strings fall back to '1.0.0'."""
        svc = self._svc()
        assert svc._increment_version("not-semver") == "1.0.0"
        assert svc._increment_version("1.0") == "1.0.0"
        assert svc._increment_version("") == "1.0.0"

    @pytest.mark.unit
    def test_non_numeric_patch_falls_back(self):
        svc = self._svc()
        assert svc._increment_version("1.0.alpha") == "1.0.0"


# ──────────────────────────────────────────────────────────────────────────────
# BusinessCaseService
# ──────────────────────────────────────────────────────────────────────────────

class TestBusinessCaseService:
    """Tests for BusinessCaseService.upsert_case_record with a mocked DB."""

    tenant_id = "tenant-business-case"

    def _make_mock_db(self, existing_record=None):
        db = MagicMock()
        db.get = AsyncMock(return_value=existing_record)
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    def _make_record(self, case_id: str):
        from layer4_agents.models.business_case_record import BusinessCaseRecord

        record = BusinessCaseRecord(
            case_id=case_id,
            workflow_id="wf-old",
            account_id=uuid4(),
            opportunity_id=None,
            status="draft",
            document_url=None,
            tenant_id=self.tenant_id,
        )
        return record

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_new_record_when_not_existing(self):
        from layer4_agents.services.business_case_service import BusinessCaseService

        db = self._make_mock_db(existing_record=None)
        svc = BusinessCaseService(db=db)

        account_id = uuid4()
        await svc.upsert_case_record(
            case_id="case-new-001",
            workflow_id="wf-123",
            account_id=account_id,
            opportunity_id="opp-456",
            status="draft",
            document_url=None,
            tenant_id=self.tenant_id,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_updates_existing_record(self):
        from layer4_agents.services.business_case_service import BusinessCaseService

        existing = self._make_record("case-existing-001")
        db = self._make_mock_db(existing_record=existing)
        svc = BusinessCaseService(db=db)

        new_account_id = uuid4()
        await svc.upsert_case_record(
            case_id="case-existing-001",
            workflow_id="wf-updated",
            account_id=new_account_id,
            opportunity_id="opp-789",
            status="in_progress",
            document_url="https://example.com/doc.pdf",
            tenant_id=self.tenant_id,
        )

        # Should NOT add a new record (update in-place)
        db.add.assert_not_called()
        assert existing.workflow_id == "wf-updated"
        assert existing.status == "in_progress"
        assert existing.document_url == "https://example.com/doc.pdf"
        db.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_returns_refreshed_record(self):
        from layer4_agents.services.business_case_service import BusinessCaseService

        existing = self._make_record("case-refresh-001")
        db = self._make_mock_db(existing_record=existing)
        svc = BusinessCaseService(db=db)

        result = await svc.upsert_case_record(
            case_id="case-refresh-001",
            workflow_id="wf-r",
            account_id=uuid4(),
            opportunity_id=None,
            status="complete",
            document_url=None,
            tenant_id=self.tenant_id,
        )

        # refresh is called on the returned record
        db.refresh.assert_called_once_with(existing)
        assert result is existing

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_with_none_opportunity_id(self):
        """Null opportunity_id is allowed (opportunity is optional)."""
        from layer4_agents.services.business_case_service import BusinessCaseService

        db = self._make_mock_db(existing_record=None)
        svc = BusinessCaseService(db=db)

        await svc.upsert_case_record(
            case_id="case-noopp",
            workflow_id="wf-x",
            account_id=uuid4(),
            opportunity_id=None,
            status="draft",
            document_url=None,
            tenant_id=self.tenant_id,
        )

        db.add.assert_called_once()
        added_record = db.add.call_args[0][0]
        assert added_record.opportunity_id is None


# ──────────────────────────────────────────────────────────────────────────────
# EncryptionService — edge cases not covered elsewhere
# ──────────────────────────────────────────────────────────────────────────────

class TestEncryptionServiceEdgeCases:
    """Additional edge-case tests for EncryptionService."""

    @pytest.fixture(autouse=True)
    def reset_encryption(self, monkeypatch):
        from collections import OrderedDict

        from layer4_agents.services.encryption_service import EncryptionService

        # Allow ephemeral key generation so tests that call encrypt/decrypt
        # work without a real CREDENTIALS_MASTER_KEY in the test environment.
        monkeypatch.setenv("ALLOW_EPHEMERAL_ENCRYPTION", "true")
        monkeypatch.delenv("CREDENTIALS_MASTER_KEY", raising=False)
        EncryptionService._MASTER_KEY = None
        EncryptionService._key_cache = OrderedDict()
        yield
        EncryptionService._MASTER_KEY = None
        EncryptionService._key_cache = OrderedDict()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rotate_key_produces_different_ciphertext(self):
        """Rotated ciphertext differs from original but decrypts to same plaintext."""
        from layer4_agents.services.encryption_service import EncryptionService

        plaintext = "sensitive-credential-data"
        original = await EncryptionService.encrypt(plaintext, key_id="v1")
        rotated = await EncryptionService.rotate_key("v1", "v2", original)

        assert rotated != original
        decrypted = await EncryptionService.decrypt(rotated, key_id="v2")
        assert decrypted == plaintext

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rotate_key_fails_with_wrong_old_key(self):
        """Rotating with wrong old key raises ValueError."""
        from layer4_agents.services.encryption_service import EncryptionService

        plaintext = "secret"
        original = await EncryptionService.encrypt(plaintext, key_id="v1")

        with pytest.raises(ValueError, match="Failed to rotate"):
            await EncryptionService.rotate_key("wrong-key", "v2", original)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_master_key_length_raises(self):
        """A master key of invalid length raises ValueError."""
        import os

        from layer4_agents.services.encryption_service import EncryptionService

        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": "tooshort"}):
            EncryptionService._MASTER_KEY = None
            with pytest.raises(ValueError, match="invalid length"):
                EncryptionService._get_master_key()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_ascii_key_id_raises(self):
        """Non-ASCII key_id raises ValueError."""
        from layer4_agents.services.encryption_service import EncryptionService

        with pytest.raises(ValueError, match="ASCII-only"):
            await EncryptionService._get_fernet("key-\u00e9")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_production_without_master_key_raises(self):
        """In production without a master key, ephemeral key generation must fail."""
        import os

        from layer4_agents.services.encryption_service import EncryptionService

        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOW_EPHEMERAL_ENCRYPTION": ""}):
            EncryptionService._MASTER_KEY = None
            with patch.dict(os.environ, {}, clear=False):
                if "CREDENTIALS_MASTER_KEY" in os.environ:
                    del os.environ["CREDENTIALS_MASTER_KEY"]
                with pytest.raises(RuntimeError, match="CREDENTIALS_MASTER_KEY is required"):
                    EncryptionService._get_master_key()
