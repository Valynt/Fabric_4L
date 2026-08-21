from __future__ import annotations

import json
import logging

from value_fabric.shared.audit.emitter import _scrub_details
from value_fabric.shared.security.redaction import (
    RedactionFilter,
    redact_credentials,
    redaction_processor,
)


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
            "api_key": "vf_test_dummy_key",
            "refresh_token": "refresh-secret",
            "stripe_payment_intent": "pi_secret",
            "nested": [{"private_key": "private-secret"}],
        }
    )
    serialized = json.dumps(scrubbed)

    for forbidden in ("vf_test_dummy_key", "refresh-secret", "pi_secret", "private-secret"):
        assert forbidden not in serialized


def test_raw_log_redaction_scrubs_pii_and_api_keys() -> None:
    rendered = redact_credentials(
        "Contact jane.doe@example.com SSN 123-45-6789 with Bearer secret-token-123 "
        "or vf_test_dummy_1234567890abcdef"
    )

    assert "jane.doe@example.com" not in rendered
    assert "123-45-6789" not in rendered
    assert "secret-token-123" not in rendered
    assert "vf_test_dummy_1234567890abcdef" not in rendered
    assert rendered.count("[REDACTED]") >= 4


def test_structured_log_redaction_processor_scrubs_nested_fields() -> None:
    payload = {
        "event": "customer_update",
        "email": "alice@example.com",
        "metadata": {
            "api_key": "vf_test_dummy_abcdef123456",
            "notes": "employee ssn 987-65-4321",
        },
        "safe": "visible",
    }

    redacted = redaction_processor(logging.getLogger("test"), "info", payload)
    serialized = json.dumps(redacted)

    assert "alice@example.com" not in serialized
    assert "vf_test_dummy_abcdef123456" not in serialized
    assert "987-65-4321" not in serialized
    assert redacted["metadata"]["api_key"] == "[REDACTED]"
    assert redacted["safe"] == "visible"


def test_stdlib_redaction_filter_scrubs_message_args_and_extra(caplog) -> None:
    logger = logging.getLogger("tests.observability.redaction")
    redaction_filter = RedactionFilter()
    logger.addFilter(redaction_filter)
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger=logger.name):
            logger.info(
                "email=%s ssn=%s",
                "bob@example.com",
                "111-22-3333",
                extra={"api_key": "vf_test_dummy_should_not_escape"},
            )
    finally:
        logger.removeFilter(redaction_filter)

    rendered = caplog.text
    assert "bob@example.com" not in rendered
    assert "111-22-3333" not in rendered
    assert "vf_test_dummy_should_not_escape" not in rendered
    assert "[REDACTED]" in rendered
