"""Tests for application-level field encryption utilities."""

from __future__ import annotations

import pytest

from value_fabric.shared.crypto.encrypted_column import (
    EncryptedString,
    _derive_blind_index_key,
    _derive_fernet_key,
    _get_fernet,
    _get_fernet_for_key,
    blind_index,
)

# A valid Fernet-compatible key for tests (32 bytes base64-encoded → 44 chars).
# This is *different* from the legacy test CREDENTIALS_MASTER_KEY so that we
# exercise the derivation path as well.
_TEST_MASTER_KEY = "test-master-key-for-pii-encryption-only-12345"


@pytest.fixture(autouse=True)
def _master_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CREDENTIALS_MASTER_KEY", _TEST_MASTER_KEY)


class TestKeyDerivation:
    def test_derive_fernet_key_produces_44_chars(self) -> None:
        key = _derive_fernet_key(_TEST_MASTER_KEY)
        assert len(key) == 44
        assert key.endswith(b"=")

    def test_derive_fernet_key_is_deterministic(self) -> None:
        assert _derive_fernet_key(_TEST_MASTER_KEY) == _derive_fernet_key(_TEST_MASTER_KEY)

    def test_get_fernet_returns_instance_when_key_set(self) -> None:
        fernet = _get_fernet()
        assert fernet is not None

    def test_get_fernet_returns_cached_instance(self) -> None:
        """Subsequent calls with the same key should return the exact same Fernet object."""
        fernet1 = _get_fernet()
        fernet2 = _get_fernet()
        assert fernet1 is fernet2

    def test_get_fernet_updates_when_key_changes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When CREDENTIALS_MASTER_KEY changes, a new Fernet instance is returned."""
        fernet1 = _get_fernet()
        monkeypatch.setenv("CREDENTIALS_MASTER_KEY", "different-secret-key-67890")
        fernet2 = _get_fernet()
        assert fernet1 is not fernet2
        assert fernet2 is _get_fernet()

    def test_get_fernet_returns_none_when_key_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CREDENTIALS_MASTER_KEY", raising=False)
        assert _get_fernet() is None


class TestBlindIndex:
    def test_produces_64_char_hex(self) -> None:
        idx = blind_index("alice@example.com")
        assert idx is not None
        assert len(idx) == 64
        assert all(c in "0123456789abcdef" for c in idx)

    def test_none_returns_none(self) -> None:
        assert blind_index(None) is None

    def test_case_insensitive(self) -> None:
        assert blind_index("Alice@Example.COM") == blind_index("alice@example.com")

    def test_whitespace_stripped(self) -> None:
        assert blind_index("  alice@example.com  ") == blind_index("alice@example.com")

    def test_deterministic(self) -> None:
        assert blind_index("bob@test.org") == blind_index("bob@test.org")

    def test_different_inputs_different_outputs(self) -> None:
        assert blind_index("a@b.com") != blind_index("c@d.com")

    def test_missing_key_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CREDENTIALS_MASTER_KEY", raising=False)
        assert blind_index("alice@example.com") is None

    def test_derive_blind_index_key_cached(self) -> None:
        """Deriving HMAC blind index key should be deterministic and cached."""
        key_bytes = b"sample-key-bytes"
        k1 = _derive_blind_index_key(key_bytes)
        k2 = _derive_blind_index_key(key_bytes)
        assert k1 == k2
        assert len(k1) == 32

    def test_explicit_key(self) -> None:
        idx1 = blind_index("alice@example.com", key="secret-one")
        idx2 = blind_index("alice@example.com", key="secret-two")
        assert idx1 is not None
        assert idx2 is not None
        assert idx1 != idx2


class TestEncryptedString:
    def test_none_passes_through_bind(self) -> None:
        col = EncryptedString()
        assert col.process_bind_param(None, dialect=None) is None

    def test_none_passes_through_result(self) -> None:
        col = EncryptedString()
        assert col.process_result_value(None, dialect=None) is None

    def test_encryption_produces_different_value(self) -> None:
        col = EncryptedString()
        plaintext = "alice@example.com"
        ciphertext = col.process_bind_param(plaintext, dialect=None)
        assert ciphertext is not None
        assert ciphertext != plaintext
        # Fernet output is URL-safe base64
        assert all(c.isalnum() or c in "-_=" for c in ciphertext)

    def test_roundtrip(self) -> None:
        col = EncryptedString()
        plaintext = "sensitive-pii-value"
        ciphertext = col.process_bind_param(plaintext, dialect=None)
        decrypted = col.process_result_value(ciphertext, dialect=None)
        assert decrypted == plaintext

    def test_unicode_roundtrip(self) -> None:
        col = EncryptedString()
        plaintext = "名前@例え.jp 🚀"
        ciphertext = col.process_bind_param(plaintext, dialect=None)
        decrypted = col.process_result_value(ciphertext, dialect=None)
        assert decrypted == plaintext

    def test_plaintext_fallback_when_key_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CREDENTIALS_MASTER_KEY", raising=False)
        col = EncryptedString()
        plaintext = "no-key-available"
        assert col.process_bind_param(plaintext, dialect=None) == plaintext

    def test_legacy_plaintext_fallback_on_decrypt(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unencrypted legacy values are returned as-is when decryption fails."""
        monkeypatch.delenv("CREDENTIALS_MASTER_KEY", raising=False)
        col = EncryptedString()
        # If a key was later added, legacy plaintext would fail InvalidToken
        # but we test the no-key path here (same return-value behaviour).
        assert col.process_result_value("legacy-plaintext", dialect=None) == "legacy-plaintext"

    def test_different_plaintexts_produce_different_ciphertexts(self) -> None:
        col = EncryptedString()
        c1 = col.process_bind_param("alice@example.com", dialect=None)
        c2 = col.process_bind_param("bob@example.com", dialect=None)
        assert c1 != c2

    def test_same_plaintext_produces_different_ciphertexts(self) -> None:
        """Fernet includes a random IV so identical plaintexts encrypt differently."""
        col = EncryptedString()
        c1 = col.process_bind_param("alice@example.com", dialect=None)
        c2 = col.process_bind_param("alice@example.com", dialect=None)
        assert c1 != c2
        # But both decrypt to the same value
        assert col.process_result_value(c1, dialect=None) == "alice@example.com"
        assert col.process_result_value(c2, dialect=None) == "alice@example.com"

    def test_impl_is_text(self) -> None:
        col = EncryptedString()
        assert str(col.impl) == "TEXT"
