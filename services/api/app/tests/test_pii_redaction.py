"""PII detection redaction tests.

These tests prove that the PII-scan service and API endpoint never return raw
sensitive values (email, phone, SSN, credit card) in their responses.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.pii_detection_service import detect_pii, pii_summary, redact_pii

from .conftest import TENANT_ALPHA, auth_headers

_HEADERS = auth_headers(TENANT_ALPHA)
_SAMPLE_TEXT = (
    "Contact alice@example.com or 555-123-4567. "
    "SSN is 123-45-6789 and card is 4111-1111-1111-1111."
)


def test_detect_pii_returns_raw_values_for_internal_use():
    """detect_pii is an internal helper and may return raw values; callers must redact."""
    findings = detect_pii(_SAMPLE_TEXT)
    assert any(f["type"] == "email" and f["value"] == "alice@example.com" for f in findings)


def test_redact_pii_masks_sensitive_values():
    redacted = redact_pii(_SAMPLE_TEXT)
    assert "alice@example.com" not in redacted
    assert "[REDACTED-EMAIL]" in redacted
    assert "555-123-4567" not in redacted
    assert "[REDACTED-PHONE]" in redacted


def test_pii_summary_does_not_expose_raw_values():
    """The API-facing summary must not echo raw PII back to clients."""
    summary = pii_summary(_SAMPLE_TEXT)
    assert summary["has_pii"] is True
    assert summary["total_findings"] > 0
    assert "email" in summary["counts"]

    raw_values = [f.get("value", "") for f in summary.get("findings", [])]
    for value in raw_values:
        assert value not in ("alice@example.com", "555-123-4567", "123-45-6789", "4111-1111-1111-1111")
        assert value.startswith("[REDACTED-")


def test_pii_summary_preserves_positions_and_types():
    summary = pii_summary(_SAMPLE_TEXT)
    emails = [f for f in summary["findings"] if f["type"] == "email"]
    assert len(emails) == 1
    assert emails[0]["start"] >= 0
    assert emails[0]["end"] > emails[0]["start"]


def test_pii_scan_endpoint_redacts_matched_values():
    """POST /evidence/{id}/pii-scan must not leak raw PII in the response body."""
    evidence_id = "ev-pii-redaction"
    with TestClient(app) as client:
        client.post(
            "/v1/accounts/acme/evidence/match",
            json={
                "id": evidence_id,
                "account_id": "acme",
                "tenant_id": TENANT_ALPHA,
                "title": "PII test",
                "excerpt": _SAMPLE_TEXT,
                "source_type": "web",
            },
            headers=_HEADERS,
        )
        response = client.post(
            f"/v1/accounts/acme/evidence/{evidence_id}/pii-scan",
            headers=_HEADERS,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["has_pii"] is True
    response_text = str(body)
    assert "alice@example.com" not in response_text
    assert "555-123-4567" not in response_text
    assert "123-45-6789" not in response_text
    assert "4111-1111-1111-1111" not in response_text
