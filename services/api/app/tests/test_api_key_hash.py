import os

import pytest

from app.core.api_key_hash import extract_key_prefix, generate_api_key, hash_api_key


@pytest.fixture(autouse=True)
def _set_hmac_secret(monkeypatch):
    monkeypatch.setenv("API_KEY_HMAC_SECRET", "test-secret-for-hashing-only-32bytes")


def test_hash_api_key_is_deterministic():
    raw = "vf_testkey123456789"
    assert hash_api_key(raw) == hash_api_key(raw)


def test_hash_api_key_uses_hmac_sha256():
    os.environ["API_KEY_HMAC_SECRET"] = "a" * 32
    digest = hash_api_key("vf_raw")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_prefix_extracts_first_chars():
    assert extract_key_prefix("vf_abcdefghij") == "vf_abcdef"


def test_generate_api_key_has_expected_shape():
    raw, key_id, prefix = generate_api_key(name="test")
    assert raw.startswith("vf_")
    assert len(raw) == 64
    assert key_id.startswith("vf_key_")
    assert prefix == raw[:12]


def test_api_key_models_import():
    from app.models.api_key import APIKeyCreateRequest, APIKeyRecord

    record = APIKeyRecord(
        key_id="vf_key_abc",
        tenant_id="tenant-1",
        name="test",
        key_hash="a" * 64,
        prefix="vf_abc",
        role="analyst",
        permissions=["benchmarks:read"],
    )
    assert record.enabled is True
