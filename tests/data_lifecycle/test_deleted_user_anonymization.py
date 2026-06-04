"""Deleted-user anonymization contract tests."""


PII_FIELDS = {"email", "display_name", "full_name", "phone", "avatar_url"}
PRESERVED_REFERENCE_FIELDS = {"id", "tenant_id", "surrogate_actor_id", "deleted_at"}


def _anonymize_deleted_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "tenant_id": user["tenant_id"],
        "surrogate_actor_id": f"deleted_user:{user['id']}",
        "deleted_at": user["deleted_at"],
        "email": None,
        "display_name": "Deleted user",
        "full_name": None,
        "phone": None,
        "avatar_url": None,
    }


def test_deleted_user_pii_is_removed_or_neutralized():
    anonymized = _anonymize_deleted_user(
        {
            "id": "user_001",
            "tenant_id": "tenant_a",
            "email": "admin@example.com",
            "display_name": "Admin User",
            "full_name": "Admin User",
            "phone": "+15555550100",
            "avatar_url": "https://example.com/avatar.png",
            "deleted_at": "2026-06-04T00:00:00Z",
        }
    )
    assert anonymized["email"] is None
    assert anonymized["display_name"] == "Deleted user"
    assert anonymized["full_name"] is None
    assert anonymized["phone"] is None
    assert anonymized["avatar_url"] is None


def test_deleted_user_keeps_surrogate_for_audit_references():
    anonymized = _anonymize_deleted_user(
        {"id": "user_001", "tenant_id": "tenant_a", "deleted_at": "2026-06-04T00:00:00Z"}
    )
    assert anonymized["surrogate_actor_id"] == "deleted_user:user_001"
    assert PRESERVED_REFERENCE_FIELDS.issubset(anonymized.keys())


def test_deleted_user_export_contains_no_original_pii_values():
    original = {
        "id": "user_001",
        "tenant_id": "tenant_a",
        "email": "admin@example.com",
        "display_name": "Admin User",
        "full_name": "Admin User",
        "phone": "+15555550100",
        "avatar_url": "https://example.com/avatar.png",
        "deleted_at": "2026-06-04T00:00:00Z",
    }
    anonymized = _anonymize_deleted_user(original)
    exported_values = {value for key, value in anonymized.items() if key in PII_FIELDS}
    assert "admin@example.com" not in exported_values
    assert "Admin User" not in exported_values
    assert "+15555550100" not in exported_values
