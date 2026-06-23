"""Real hostile API key payloads for security regression testing.

These records exercise the API key resolver with malformed, malicious,
and edge-case inputs to verify that:
- hostile keys do not authenticate
- the resolver does not crash
- tenant scoping is not bypassed
- raw key material is not leaked in errors or logs
"""

from __future__ import annotations


def hostile_api_key_records() -> list[dict]:
    """Return a suite of hostile API key records."""
    return [
        # 1. Empty key payload
        {
            "key_id": "",
            "tenant_id": None,
            "user_id": None,
            "role": "read_only",
            "enabled": True,
        },
        # 2. Whitespace-only key
        {
            "key_id": "   ",
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 3. Malformed prefix (SQL-like injection in key_id)
        {
            "key_id": "'; DROP TABLE api_keys; --",
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 4. Overly long key
        {
            "key_id": "vf_" + "A" * 4096,
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 5. Shell metacharacters
        {
            "key_id": "vf_$(cat /etc/passwd)",
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 6. Newline / header injection
        {
            "key_id": "vf_test\nX-Forwarded-For: 127.0.0.1",
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 7. Unicode / confusable characters
        {
            "key_id": "vf_tëst_κλειδί_鍵",
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 8. Null byte-like payload
        {
            "key_id": "vf_test\x00_admin",
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 9. Valid-looking but unknown key (well-formed UUID, no tenant)
        {
            "key_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
            "tenant_id": None,
            "user_id": None,
            "role": "admin",
            "enabled": True,
        },
        # 10. Wrong tenant key (valid structure but empty tenant)
        {
            "key_id": "vf_prod_abc123",
            "tenant_id": "",
            "user_id": "usr-1",
            "role": "admin",
            "enabled": True,
        },
        # 11. Revoked / disabled key
        {
            "key_id": "vf_revoked_xyz",
            "tenant_id": "tenant-1",
            "user_id": "usr-1",
            "role": "admin",
            "enabled": False,
        },
        # 12. Invalid tenant_id type (non-UUID string)
        {
            "key_id": "vf_bad_tenant",
            "tenant_id": "not-a-uuid",
            "user_id": "usr-1",
            "role": "admin",
            "enabled": True,
        },
        # 13. Record with missing required fields entirely
        {
            "enabled": True,
        },
        # 14. Record with None values for all identity fields
        {
            "key_id": None,
            "tenant_id": None,
            "user_id": None,
            "role": None,
            "enabled": True,
        },
    ]
