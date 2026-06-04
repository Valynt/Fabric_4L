from __future__ import annotations

import json

from value_fabric.shared.audit.emitter import _scrub_details


def test_audit_log_scrubber_redacts_security_and_payment_fields() -> None:
    payload = {
        "password": "correct horse battery staple",
        "session_token": "session-secret",
        "Authorization": "Bearer token-secret",
        "payment_details": {"card_number": "4242424242424242", "last4": "4242"},
        "metadata": {"client_secret": "stripe-secret", "safe": "ok"},
        "safe": "visible",
    }

    scrubbed = _scrub_details(payload)

    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["session_token"] == "[REDACTED]"
    assert scrubbed["Authorization"] == "[REDACTED]"
    assert scrubbed["payment_details"] == "[REDACTED]"
    assert scrubbed["metadata"]["client_secret"] == "[REDACTED]"
    assert scrubbed["metadata"]["safe"] == "ok"
    assert scrubbed["safe"] == "visible"


def test_redacted_log_payload_contains_no_sensitive_sample_values() -> None:
    scrubbed = _scrub_details(
        {
            "api_key": "vf_live_key",
            "refresh_token": "refresh-secret",
            "stripe_payment_intent": "pi_secret",
            "nested": [{"private_key": "private-secret"}],
        }
    )
    serialized = json.dumps(scrubbed)

    for forbidden in ("vf_live_key", "refresh-secret", "pi_secret", "private-secret"):
        assert forbidden not in serialized
