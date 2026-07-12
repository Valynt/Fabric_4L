"""Account export lifecycle contract tests."""

import hashlib
import json

EXPORT_SCHEMA_VERSION = "data-lifecycle-export.v1"
REQUIRED_TOP_LEVEL_FIELDS = [
    "schema_version",
    "export_id",
    "export_scope",
    "tenant_id",
    "subject",
    "generated_at",
    "requested_by",
    "data_categories",
    "resources",
    "redactions",
    "audit_chain",
    "checksums",
]
PROHIBITED_EXPORT_KEYS = {
    "password",
    "password_hash",
    "payment_secret",
    "provider_token",
    "raw_auth_claims",
    "stripe_secret_key",
}


def _canonical_payload_without_checksum(payload: dict) -> bytes:
    unsigned = json.loads(json.dumps(payload))
    unsigned["checksums"]["payload"] = ""
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _with_checksum(payload: dict) -> dict:
    payload = json.loads(json.dumps(payload))
    payload["checksums"]["payload"] = hashlib.sha256(_canonical_payload_without_checksum(payload)).hexdigest()
    return payload


def _sample_account_export() -> dict:
    return _with_checksum(
        {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "export_id": "exp_account_001",
            "export_scope": "account",
            "tenant_id": "tenant_a",
            "subject": {"type": "account", "id": "acct_001"},
            "generated_at": "2026-06-04T00:00:00Z",
            "requested_by": {"actor_id": "user_admin", "actor_type": "user", "tenant_id": "tenant_a"},
            "data_categories": ["account_profile", "workflow_outputs", "derived_knowledge"],
            "resources": {
                "accounts": [{"id": "acct_001", "tenant_id": "tenant_a", "name": "Acme Corp"}],
                "value_cases": [{"id": "case_001", "tenant_id": "tenant_a", "account_id": "acct_001"}],
            },
            "redactions": [{"path": "resources.accounts[].crm_access_token", "reason": "secret"}],
            "audit_chain": [{"event": "account.exported", "tenant_id": "tenant_a", "subject_id": "acct_001"}],
            "checksums": {"algorithm": "sha256", "payload": ""},
        }
    )


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def test_account_export_has_stable_top_level_shape():
    payload = _sample_account_export()
    assert list(payload.keys()) == REQUIRED_TOP_LEVEL_FIELDS
    assert payload["schema_version"] == EXPORT_SCHEMA_VERSION
    assert payload["export_scope"] == "account"
    assert payload["subject"] == {"type": "account", "id": "acct_001"}


def test_account_export_is_tenant_scoped_and_excludes_foreign_records():
    payload = _sample_account_export()
    assert payload["tenant_id"] == payload["requested_by"]["tenant_id"]
    for records in payload["resources"].values():
        for record in records:
            assert record["tenant_id"] == payload["tenant_id"]


def test_account_export_checksum_is_deterministic():
    payload = _sample_account_export()
    expected = hashlib.sha256(_canonical_payload_without_checksum(payload)).hexdigest()
    assert payload["checksums"] == {"algorithm": "sha256", "payload": expected}


def test_account_export_excludes_secret_material():
    payload = _sample_account_export()
    exported_keys = {key.lower() for key in _walk_keys(payload)}
    assert exported_keys.isdisjoint(PROHIBITED_EXPORT_KEYS)
