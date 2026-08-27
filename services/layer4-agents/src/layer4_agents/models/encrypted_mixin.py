# ---------------------------------------------------------------------------
# PII Encryption Mixin — Production-grade encryption at rest for Layer 4
# ---------------------------------------------------------------------------
#
"""SQLAlchemy mixin for transparent PII encryption at rest.

Provides declarative encryption of personally identifiable information (PII)
using the canonical ``EncryptedString`` type from
``value_fabric.shared.crypto``.  Blind indexes are generated for fields
that require exact-match lookups (email, phone) without exposing plaintext.

Usage::

    class Contact(Base, PIIMixin):
        __tablename__ = "contacts"
        __pii_config__ = {
            "email": {"searchable": True},
            "phone": {"searchable": True},
            "ssn": {"searchable": False},
        }

        id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
        name: Mapped[str] = mapped_column(String(255))
        # email, email_hash, phone, phone_hash, ssn columns are created
        # automatically by the mixin.

Querying by blind index::

    email_hash = PIIMixin.hash_for_query("alice@example.com")
    contact = session.query(Contact).filter(Contact.email_hash == email_hash).first()
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, ClassVar, cast

from sqlalchemy import Column, String, event
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, Mapper, declared_attr, mapped_column
from value_fabric.shared.crypto import EncryptedString, blind_index

logger = logging.getLogger(__name__)

#: PII fields that are encrypted by default when using the mixin.
#: Each entry is a field name; the ``__pii_config__`` dict on the
#: concrete model controls per-field options (searchable, max_length, …).
DEFAULT_PII_FIELDS: dict[str, dict[str, Any]] = {
    "email": {"searchable": True, "max_length": 255},
    "phone": {"searchable": True, "max_length": 50},
    "ssn": {"searchable": False, "max_length": 50},
    "address_line1": {"searchable": False, "max_length": 255},
    "bank_account": {"searchable": False, "max_length": 100},
}

#: Env var that controls the active encryption key version.
#: When bumped, new writes use the new key; legacy ciphertext is
#: still decrypted (EncryptedString handles legacy fallback).
_KEY_VERSION_ENV_VAR: str = "ENCRYPTION_KEY_VERSION"

#: Production marker — when True and no master key is configured,
#: model instantiation raises RuntimeError.
_PRODUCTION_ENFORCE_ENCRYPTION: bool = (
    os.getenv("ENFORCE_PII_ENCRYPTION", "").strip().lower() == "true"
)


class _PIIDescriptor:
    """Descriptor that intercepts attribute access for PII fields.

    Transparently routes reads/writes through the EncryptedString
    column while exposing a plain Python attribute interface.
    """

    def __init__(self, field_name: str, encrypted_col_name: str) -> None:
        self.field_name = field_name
        self.encrypted_col_name = encrypted_col_name
        self.__doc__ = f"Encrypted PII field: {field_name}"

    def __set__(self, instance: Any, value: str | None) -> None:
        if instance is None:
            raise AttributeError(f"Cannot set {self.field_name} on class")
        setattr(instance, self.encrypted_col_name, value)

    def __get__(self, instance: Any, owner: type) -> str | None:
        if instance is None:
            return self  # type: ignore[return-value]
        return getattr(instance, self.encrypted_col_name, None)


class PIIMixin:
    """Mixin that adds encrypted-at-rest PII columns to a SQLAlchemy model.

    Subclasses **must** define ``__pii_config__`` as a class attribute::

        __pii_config__: ClassVar[dict[str, dict[str, Any]]] = {
            "email": {"searchable": True},
            "phone": {"searchable": True},
            "ssn": {"searchable": False},
        }

    The following columns are created automatically:
    - ``<field>_encrypted`` — stores Fernet-encrypted ciphertext
    - ``<field>_hash``      — HMAC-SHA256 blind index (only when ``searchable=True``)
    - ``pii_key_version``   — integer tracking the encryption key version at write time
    """

    __pii_config__: ClassVar[dict[str, dict[str, Any]]] = {}

    @declared_attr.directive
    @classmethod
    def pii_key_version(cls) -> Mapped[str]:
        """Track the encryption key version used for the most recent write.

        Enables deterministic re-encryption when rotating keys: select rows
        where ``pii_key_version < ENCRYPTION_KEY_VERSION`` and re-write.
        """
        return mapped_column(String(8), nullable=True, default="1")

    @classmethod
    def __declare_last__(cls) -> None:
        """Late-binding hook to validate PII configuration after mapper init."""
        if not cls.__pii_config__:
            logger.warning(
                "PIIMixin subclass %s has empty __pii_config__; no PII columns created.",
                cls.__name__,
            )
            return

        if _PRODUCTION_ENFORCE_ENCRYPTION:
            master_key = os.getenv("CREDENTIALS_MASTER_KEY", "").strip()
            if not master_key:
                raise RuntimeError(
                    "CREDENTIALS_MASTER_KEY is required when ENFORCE_PII_ENCRYPTION=true. "
                    f"Model {cls.__name__} uses PIIMixin and cannot operate without encryption."
                )

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Skip processing for the mixin itself
        if cls.__name__ == "PIIMixin":
            return

        config = getattr(cls, "__pii_config__", None)
        if not config:
            return

        # Validate config keys against known PII fields
        unknown = set(config.keys()) - set(DEFAULT_PII_FIELDS.keys())
        if unknown:
            raise ValueError(
                f"Unknown PII fields in __pii_config__: {sorted(unknown)}. "
                f"Supported fields: {sorted(DEFAULT_PII_FIELDS.keys())}"
            )

        for field_name, field_cfg in config.items():
            cls._add_pii_field(field_name, field_cfg)

    @classmethod
    def _add_pii_field(cls, field_name: str, field_cfg: dict[str, Any]) -> None:
        """Dynamically add encrypted column and optional blind-index column."""
        default_cfg = DEFAULT_PII_FIELDS.get(field_name, {})
        searchable = field_cfg.get("searchable", default_cfg.get("searchable", False))

        encrypted_col_name = f"{field_name}_encrypted"
        hash_col_name = f"{field_name}_hash"

        # --- Encrypted storage column ---
        # Use EncryptedString TypeDecorator for transparent encrypt/decrypt.
        encrypted_col = Column(encrypted_col_name, EncryptedString(), nullable=True)
        setattr(cls, encrypted_col_name, encrypted_col)

        # --- Blind-index column (for exact-match queries) ---
        if searchable:
            hash_col = Column(hash_col_name, String(64), nullable=True, index=True)
            setattr(cls, hash_col_name, hash_col)
        else:
            # Non-searchable fields still get a hash column but without an index
            # so that equality checks work in Python without exposing plaintext.
            hash_col = Column(hash_col_name, String(64), nullable=True, index=False)
            setattr(cls, hash_col_name, hash_col)

        # --- Hybrid property for transparent access ---
        def _make_getter(enc_name: str) -> Any:
            def getter(self: Any) -> str | None:
                return getattr(self, enc_name, None)

            return getter

        def _make_setter(enc_name: str, hash_name: str, is_searchable: bool) -> Any:
            def setter(self: Any, value: str | None) -> None:
                setattr(self, enc_name, value)
                # Re-compute blind index on write
                if value is not None:
                    idx = blind_index(value)
                    setattr(self, hash_name, idx)
                else:
                    setattr(self, hash_name, None)
                # Track key version for rotation support
                key_ver = os.getenv(_KEY_VERSION_ENV_VAR, "1").strip()
                if key_ver:
                    self.pii_key_version = key_ver

            return setter

        setattr(
            cls,
            field_name,
            hybrid_property(
                fget=_make_getter(encrypted_col_name),
                fset=_make_setter(encrypted_col_name, hash_col_name, searchable),
            ),
        )

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @classmethod
    def hash_for_query(cls, plaintext: str | None) -> str | None:
        """Return the blind-index hash for an exact-match query.

        Example::

            q = session.query(Contact).filter(
                Contact.email_hash == PIIMixin.hash_for_query("alice@example.com")
            )
        """
        return cast(str | None, blind_index(plaintext))

    @classmethod
    def pii_fields(cls) -> list[str]:
        """Return the list of configured PII field names."""
        return list(getattr(cls, "__pii_config__", {}).keys())

    @classmethod
    def searchable_pii_fields(cls) -> list[str]:
        """Return PII fields that have a blind index for exact-match queries."""
        return [
            f
            for f, cfg in getattr(cls, "__pii_config__", {}).items()
            if cfg.get("searchable", DEFAULT_PII_FIELDS.get(f, {}).get("searchable", False))
        ]

    def pii_needs_reencryption(self) -> bool:
        """Return True if this record was encrypted with an older key version.

        Use this in a background job to select rows for proactive re-encryption
        after a key rotation.
        """
        current_version = os.getenv(_KEY_VERSION_ENV_VAR, "1").strip()
        record_version = getattr(self, "pii_key_version", None) or "1"
        return record_version != current_version

    def rotate_pii_encryption(self) -> None:
        """Re-encrypt all PII fields with the current key version.

        Idempotent: reading the hybrid property decrypts, writing re-encrypts
        with the active key.  Call ``session.commit()`` after invoking.
        """
        for field_name in self.pii_fields():
            current_value = getattr(self, field_name, None)
            # Setting the hybrid property triggers encryption + blind-index update
            setattr(self, field_name, current_value)


# ---------------------------------------------------------------------------
# SQLAlchemy event listener: auto-populate blind indexes on INSERT/UPDATE
# ---------------------------------------------------------------------------


@event.listens_for(PIIMixin, "before_insert", propagate=True)
@event.listens_for(PIIMixin, "before_update", propagate=True)
def _pii_auto_populate_hash(mapper: Mapper[PIIMixin], connection: Any, target: PIIMixin) -> None:
    """Ensure blind indexes are populated before persistence.

    Acts as a defense-in-depth guard: even if the hybrid-property setter
    is bypassed (e.g., via ``__dict__`` mutation), the blind index is
    recomputed from the encrypted column value at flush time.
    """
    config = getattr(target, "__pii_config__", {})
    for field_name, field_cfg in config.items():
        encrypted_col_name = f"{field_name}_encrypted"
        hash_col_name = f"{field_name}_hash"
        encrypted_value = getattr(target, encrypted_col_name, None)
        if encrypted_value is not None:
            # If the value is already encrypted, we can't re-index without
            # decrypting.  The hybrid-property setter handles this on normal
            # writes.  This listener only fixes cases where the hash is missing.
            existing_hash = getattr(target, hash_col_name, None)
            if existing_hash is None:
                # Attempt to decrypt and re-index (best-effort)
                try:
                    from value_fabric.shared.crypto.encrypted_column import _get_fernet

                    fernet = _get_fernet()
                    if fernet is not None:
                        plaintext = fernet.decrypt(encrypted_value.encode("ascii")).decode("utf-8")
                        setattr(target, hash_col_name, blind_index(plaintext))
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.debug(
                        "Could not auto-populate blind index for %s on %s",
                        field_name,
                        target,
                        exc_info=True,
                    )
        else:
            setattr(target, hash_col_name, None)


# ---------------------------------------------------------------------------
# Integration with the Account model (example migration path)
# ---------------------------------------------------------------------------
# To adopt PIIMixin on an existing model that already uses EncryptedString
# directly (e.g., Account.headquarters, Account.owner_email):
#
#   class Account(Base, PIIMixin):
#       __tablename__ = "accounts"
#       __pii_config__ = {
#           "email": {"searchable": True},      # replaces owner_email
#           "address_line1": {"searchable": False},  # replaces headquarters
#       }
#       ...
#
# A database migration should:
#   1. Add ``*_encrypted`` and ``*_hash`` columns
#   2. Migrate data from old columns to new encrypted columns
#   3. Drop old columns (after verification)
# ---------------------------------------------------------------------------


__all__ = ["PIIMixin", "DEFAULT_PII_FIELDS"]
