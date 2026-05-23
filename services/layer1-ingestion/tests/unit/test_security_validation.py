from src.shared.security_validation import (
    REDACTED,
    contains_inline_secret_material,
    is_valid_credential_reference,
    sanitize_for_logging,
)


def test_detects_inline_secret_material():
    payload = {"authentication": {"username": "a", "password": "super-secret"}}
    assert contains_inline_secret_material(payload)


def test_credential_reference_validation():
    assert is_valid_credential_reference("vault://team/service/connector")
    assert not is_valid_credential_reference("plain-text-secret")


def test_sanitize_for_logging_redacts_sensitive_keys():
    payload = {"config": {"api_key": "secret", "nested": {"client_secret": "secret2"}}}
    sanitized = sanitize_for_logging(payload)
    assert sanitized["config"]["api_key"] == REDACTED
    assert sanitized["config"]["nested"]["client_secret"] == REDACTED
