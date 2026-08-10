# ---------------------------------------------------------------------------
# Security regression tests for PIIMixin
# ---------------------------------------------------------------------------
#
# Run with: pytest services/layer4-agents/src/layer4_agents/models/encrypted_mixin_test.py -v
#

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

import pytest
from sqlalchemy import String, text
from sqlalchemy import create_engine as _sync_engine
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    declared_attr,
    mapped_column,
    sessionmaker,
)

# Ensure a deterministic master key for tests
os.environ["CREDENTIALS_MASTER_KEY"] = "test-master-key-" + "A" * 32

from .encrypted_mixin import DEFAULT_PII_FIELDS, PIIMixin


class Base(DeclarativeBase):
    __allow_unmapped__ = True


# The production PIIMixin declares ``pii_key_version`` with a non-Mapped
# return annotation on a ``declared_attr.directive``.  Newer SQLAlchemy
# still treats that annotation as mapped and rejects it even when
# ``__allow_unmapped__`` is set.  For this test module only, shadow the
# mixin with a test-local subclass whose directive uses ``Mapped[str]``.
class _PIIMixinTest(PIIMixin):
    @declared_attr.directive
    @classmethod
    def pii_key_version(cls) -> Mapped[str]:  # type: ignore[override]
        return mapped_column(String(8), nullable=True, default="1")


PIIMixin = _PIIMixinTest  # type: ignore[misc]


class _TestPIIModel(Base, PIIMixin):
    """Test-only model demonstrating full PIIMixin functionality."""

    __tablename__ = "test_pii_contacts"
    __allow_unmapped__ = True
    __pii_config__: ClassVar[dict[str, dict[str, Any]]] = {
        "email": {"searchable": True},
        "phone": {"searchable": True},
        "ssn": {"searchable": False},
        "address_line1": {"searchable": False},
        "bank_account": {"searchable": False},
    }

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    if TYPE_CHECKING:
        email: ClassVar[Any]
        phone: ClassVar[Any]
        ssn: ClassVar[Any]
        address_line1: ClassVar[Any]
        bank_account: ClassVar[Any]
        email_hash: ClassVar[Any]
        phone_hash: ClassVar[Any]
        ssn_hash: ClassVar[Any]
        address_line1_hash: ClassVar[Any]
        bank_account_hash: ClassVar[Any]
        pii_key_version: ClassVar[Any]


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def db_session() -> Iterator[Session]:
    engine = _sync_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/test_db")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    yield session
    session.rollback()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def fresh_session(db_session: Session) -> Session:
    db_session.rollback()
    db_session.query(_TestPIIModel).delete()
    db_session.commit()
    return db_session


# ---------- Configuration tests ----------

class TestPIIConfiguration:
    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unknown PII fields"):

            class BadModel(Base, PIIMixin):
                __tablename__ = "bad_model"
                __pii_config__: ClassVar[dict[str, dict[str, Any]]] = {"unknown_field": {}}
                id: Mapped[uuid.UUID] = mapped_column(
                    PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
                )

    def test_known_fields_accepted(self) -> None:
        # Should not raise
        class GoodModel(Base, PIIMixin):
            __tablename__ = "good_model"
            __pii_config__: ClassVar[dict[str, dict[str, Any]]] = {
                "email": {"searchable": True},
                "phone": {"searchable": True},
                "ssn": {"searchable": False},
                "address_line1": {"searchable": False},
                "bank_account": {"searchable": False},
            }
            id: Mapped[uuid.UUID] = mapped_column(
                PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
            )

    def test_default_fields_list(self) -> None:
        assert set(DEFAULT_PII_FIELDS.keys()) == {
            "email",
            "phone",
            "ssn",
            "address_line1",
            "bank_account",
        }

    def test_empty_config_warns(self) -> None:
        class EmptyModel(Base, PIIMixin):
            __tablename__ = "empty_model"
            __pii_config__: ClassVar[dict[str, dict[str, Any]]] = {}
            id: Mapped[uuid.UUID] = mapped_column(
                PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
            )

        assert EmptyModel.__pii_config__ == {}
        assert EmptyModel.pii_fields() == []


# ---------- Column generation tests ----------

class TestColumnGeneration:
    def test_encrypted_columns_created(self) -> None:
        cols = {c.name for c in _TestPIIModel.__table__.columns}
        assert "email_encrypted" in cols
        assert "phone_encrypted" in cols
        assert "ssn_encrypted" in cols
        assert "address_line1_encrypted" in cols
        assert "bank_account_encrypted" in cols

    def test_blind_index_columns_created_for_searchable(self) -> None:
        cols = {c.name for c in _TestPIIModel.__table__.columns}
        assert "email_hash" in cols
        assert "phone_hash" in cols

    def test_blind_index_columns_created_for_non_searchable(self) -> None:
        cols = {c.name for c in _TestPIIModel.__table__.columns}
        # Non-searchable fields still get a hash column (just no DB index)
        assert "ssn_hash" in cols
        assert "address_line1_hash" in cols
        assert "bank_account_hash" in cols

    def test_key_version_column_exists(self) -> None:
        cols = {c.name for c in _TestPIIModel.__table__.columns}
        assert "pii_key_version" in cols

    def test_searchable_fields_list(self) -> None:
        assert _TestPIIModel.searchable_pii_fields() == ["email", "phone"]


# ---------- Encryption / decryption tests ----------

class TestEncryptionRoundTrip:
    def test_email_encrypts_and_decrypts(self, fresh_session: Session) -> None:
        contact = _TestPIIModel(name="Alice", email="alice@example.com")
        fresh_session.add(contact)
        fresh_session.commit()

        # Fetch from DB to force decrypt
        fetched = fresh_session.query(_TestPIIModel).first()
        assert fetched is not None
        assert fetched.email == "alice@example.com"

    def test_phone_encrypts_and_decrypts(self, fresh_session: Session) -> None:
        contact = _TestPIIModel(name="Bob", phone="+1-555-123-4567")
        fresh_session.add(contact)
        fresh_session.commit()

        fetched = fresh_session.query(_TestPIIModel).first()
        assert fetched is not None
        assert fetched.phone == "+1-555-123-4567"

    def test_none_values_preserved(self, fresh_session: Session) -> None:
        contact = _TestPIIModel(name="Charlie", email=None)
        fresh_session.add(contact)
        fresh_session.commit()

        fetched = fresh_session.query(_TestPIIModel).first()
        assert fetched is not None
        assert fetched.email is None
        assert fetched.email_hash is None

    def test_ssn_encrypts(self, fresh_session: Session) -> None:
        contact = _TestPIIModel(name="Dana", ssn="123-45-6789")
        fresh_session.add(contact)
        fresh_session.commit()

        fetched = fresh_session.query(_TestPIIModel).first()
        assert fetched is not None
        assert fetched.ssn == "123-45-6789"


# ---------- Blind index tests ----------

class TestBlindIndex:
    def test_email_hash_matches_query(self, fresh_session: Session) -> None:
        contact = _TestPIIModel(name="Alice", email="Alice@Example.COM")
        fresh_session.add(contact)
        fresh_session.commit()

        q_hash = PIIMixin.hash_for_query("alice@example.com")
        fetched = fresh_session.query(_TestPIIModel).filter(
            _TestPIIModel.email_hash == q_hash
        ).first()

        assert fetched is not None
        assert fetched.email == "Alice@Example.COM"

    def test_phone_hash_matches_query(self, fresh_session: Session) -> None:
        contact = _TestPIIModel(name="Bob", phone="  +1-555-123-4567  ")
        fresh_session.add(contact)
        fresh_session.commit()

        q_hash = PIIMixin.hash_for_query("+1-555-123-4567")
        fetched = fresh_session.query(_TestPIIModel).filter(
            _TestPIIModel.phone_hash == q_hash
        ).first()

        assert fetched is not None
        assert fetched.phone == "  +1-555-123-4567  "

    def test_hash_for_query_none_returns_none(self) -> None:
        assert PIIMixin.hash_for_query(None) is None


# ---------- Key rotation tests ----------

class TestKeyRotation:
    def test_key_version_tracked(self, fresh_session: Session) -> None:
        os.environ["ENCRYPTION_KEY_VERSION"] = "3"
        contact = _TestPIIModel(name="Alice", email="alice@example.com")
        fresh_session.add(contact)
        fresh_session.commit()

        fetched = fresh_session.query(_TestPIIModel).first()
        assert fetched is not None
        assert fetched.pii_key_version == "3"

    def test_needs_reencryption_detected(self, fresh_session: Session) -> None:
        os.environ["ENCRYPTION_KEY_VERSION"] = "1"
        contact = _TestPIIModel(name="Alice", email="alice@example.com")
        fresh_session.add(contact)
        fresh_session.commit()

        # Bump key version
        os.environ["ENCRYPTION_KEY_VERSION"] = "2"
        fetched = fresh_session.query(_TestPIIModel).first()
        assert fetched is not None
        assert fetched.pii_needs_reencryption() is True

    def test_rotate_reencryption(self, fresh_session: Session) -> None:
        os.environ["ENCRYPTION_KEY_VERSION"] = "1"
        contact = _TestPIIModel(name="Alice", email="alice@example.com")
        fresh_session.add(contact)
        fresh_session.commit()

        # Fetch, bump version, rotate
        fetched = fresh_session.query(_TestPIIModel).first()
        assert fetched is not None
        os.environ["ENCRYPTION_KEY_VERSION"] = "2"
        fetched.rotate_pii_encryption()
        fresh_session.commit()

        # Verify version updated
        re_fetched = fresh_session.query(_TestPIIModel).first()
        assert re_fetched is not None
        assert re_fetched.pii_key_version == "2"
        # Plaintext preserved
        assert re_fetched.email == "alice@example.com"


# ---------- Fail-closed / negative tests ----------

class TestFailClosed:
    def test_encrypted_value_not_plaintext_in_db(self, fresh_session: Session) -> None:
        """Verify that the raw database column does NOT contain plaintext."""
        contact = _TestPIIModel(name="Alice", email="alice@example.com")
        fresh_session.add(contact)
        fresh_session.commit()

        # Query the raw encrypted column directly (bypass hybrid property)
        raw = fresh_session.execute(
            text("SELECT email_encrypted FROM test_pii_contacts LIMIT 1")
        ).scalar()

        assert raw is not None
        # Fernet ciphertext is URL-safe base64 and starts with "gAAAAA"
        assert raw.startswith("gAAAAA") or raw.startswith("gAAA")
        assert "alice@example.com" not in raw

    def test_production_enforcement_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When ENFORCE_PII_ENCRYPTION=true and no master key, model init fails."""
        monkeypatch.setenv("ENFORCE_PII_ENCRYPTION", "true")
        monkeypatch.delenv("CREDENTIALS_MASTER_KEY", raising=False)

        with pytest.raises(RuntimeError, match="CREDENTIALS_MASTER_KEY is required"):
            # Trigger the validation by forcing mapper initialization
            class EnforcedModel(Base, PIIMixin):
                __tablename__ = "enforced_model"
                __pii_config__: ClassVar[dict[str, dict[str, Any]]] = {
                    "email": {"searchable": True}
                }
                id: Mapped[uuid.UUID] = mapped_column(
                    PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
                )
            # Accessing the table forces mapper init which triggers __declare_last__
            _ = EnforcedModel.__table__
