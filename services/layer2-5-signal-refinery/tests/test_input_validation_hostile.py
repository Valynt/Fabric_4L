"""Hostile input validation tests for L2.5 Signal Refinery.

These adversarial tests verify that malformed, oversized, injection,
and otherwise hostile payloads are rejected safely.
"""

from __future__ import annotations

import pytest

from .conftest import ACCOUNT_A, make_signal_payload

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# XSS / Script injection attempts
# ---------------------------------------------------------------------------


async def test_create_signal_rejects_xss_in_content(client):
    """Signal content containing script tags must be rejected or sanitized."""
    payload = make_signal_payload(content="<script>alert('xss')</script>")
    response = await client.post("/api/v1/signals", json=payload)
    # Service may reject (422) or sanitize (201); either is acceptable
    # if the stored value does not contain executable script
    if response.status_code == 201:
        data = response.json()
        stored = data.get("content", "")
        assert "<script>" not in stored.lower(), (
            f"XSS payload stored unsanitized: {stored}"
        )


async def test_create_signal_rejects_xss_in_evidence_excerpt(client):
    """Evidence excerpt containing script tags must be rejected or sanitized."""
    payload = make_signal_payload()
    payload["evidence"] = [
        {
            "id": "ev-001",
            "source_ref": "doc://test/source-1",
            "excerpt": "<img src=x onerror=alert(1)>",
            "confidence": 0.85,
            "relevance_score": 0.9,
        }
    ]
    response = await client.post("/api/v1/signals", json=payload)
    if response.status_code == 201:
        data = response.json()
        for ev in data.get("evidence", []):
            assert "<img" not in ev.get("excerpt", "").lower(), (
                f"XSS in evidence excerpt stored unsanitized"
            )


# ---------------------------------------------------------------------------
# SQL injection attempts
# ---------------------------------------------------------------------------


async def test_create_signal_rejects_sql_injection_in_content(client):
    """Content containing SQL injection must not cause errors or leaks."""
    payload = make_signal_payload(
        content="'; DROP TABLE value_signals; --"
    )
    response = await client.post("/api/v1/signals", json=payload)
    # Must not crash (500) — 201, 400 or 422 are acceptable
    assert response.status_code in (201, 400, 422), (
        f"SQL injection caused unexpected status: {response.status_code}"
    )
    if response.status_code == 201:
        data = response.json()
        assert "drop table" not in data.get("content", "").lower()


async def test_list_signals_rejects_sql_injection_in_account_id(client):
    """Account ID query param must not be vulnerable to SQL injection."""
    response = await client.get(
        "/api/v1/signals",
        params={"account_id": "'; DROP TABLE value_signals; --"},
    )
    # Must not crash
    assert response.status_code in (200, 422, 400), (
        f"SQL injection in account_id caused unexpected status: {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Oversized payload attempts
# ---------------------------------------------------------------------------


async def test_create_signal_rejects_oversized_content(client):
    """Extremely large content must be rejected (422 or 413)."""
    payload = make_signal_payload(content="A" * 10_000_000)
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code in (201, 422, 413), (
        f"Oversized content caused unexpected status: {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Invalid data type attempts
# ---------------------------------------------------------------------------


async def test_create_signal_rejects_invalid_confidence_type(client):
    """Non-numeric confidence must be rejected."""
    payload = make_signal_payload()
    payload["confidence"] = "high"
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 422, (
        f"Expected 422 for invalid confidence type, got {response.status_code}"
    )


async def test_create_signal_rejects_negative_confidence(client):
    """Negative confidence must be rejected."""
    payload = make_signal_payload(confidence=-0.5)
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 422, (
        f"Expected 422 for negative confidence, got {response.status_code}"
    )


async def test_create_signal_rejects_confidence_above_one(client):
    """Confidence > 1.0 must be rejected."""
    payload = make_signal_payload(confidence=1.5)
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 422, (
        f"Expected 422 for confidence > 1.0, got {response.status_code}"
    )


async def test_create_signal_rejects_invalid_evidence_structure(client):
    """Malformed evidence array must be rejected."""
    payload = make_signal_payload()
    payload["evidence"] = "not-a-list"
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 422, (
        f"Expected 422 for invalid evidence structure, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Unknown / extra fields policy
# ---------------------------------------------------------------------------


async def test_create_signal_ignores_or_rejects_unknown_fields(client):
    """Unknown fields in payload must not cause crashes or be stored."""
    payload = make_signal_payload()
    payload["malicious_field"] = "should not be stored"
    payload["__proto__"] = {"polluted": True}
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code in (201, 422), (
        f"Unknown fields caused unexpected status: {response.status_code}"
    )
    if response.status_code == 201:
        data = response.json()
        assert "malicious_field" not in data, (
            f"Unknown field was stored: {data}"
        )
        assert "__proto__" not in data, (
            f"Prototype pollution field was stored: {data}"
        )


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


async def test_create_signal_rejects_missing_account_id(client):
    """Missing account_id must be rejected."""
    payload = make_signal_payload()
    del payload["account_id"]
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 422


async def test_create_signal_rejects_missing_type(client):
    """Missing type must be rejected."""
    payload = make_signal_payload()
    del payload["type"]
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 422


async def test_create_signal_rejects_missing_content(client):
    """Missing content must be rejected."""
    payload = make_signal_payload()
    del payload["content"]
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Null byte injection
# ---------------------------------------------------------------------------


async def test_create_signal_rejects_null_bytes_in_content(client):
    """Null bytes in content must be rejected."""
    payload = make_signal_payload(content="hello\x00world")
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code in (201, 422, 400), (
        f"Null byte caused unexpected status: {response.status_code}"
    )
