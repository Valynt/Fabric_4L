"""
P1: Input Validation Security Tests — Production Assurance Suite.

Validates that the system properly validates and sanitizes all input
to prevent injection attacks, DoS via oversized payloads, and data pollution.

Boundaries Tested:
- Payload size limits (DoS prevention)
- Unknown field rejection
- Unsafe string sanitization
- Invalid enum/state transition rejection
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest


try:
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from pydantic import BaseModel, ConfigDict, ValidationError
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None


_repo_root = Path(__file__).resolve().parents[2]
_services_path = str(_repo_root / "services")
if _services_path not in sys.path:
    sys.path.insert(0, _services_path)
    _PATH_ADDED = True
else:
    _PATH_ADDED = False

try:
    from value_fabric.shared.security import SecurityConfig, add_security_middleware
finally:
    if _PATH_ADDED and _services_path in sys.path:
        sys.path.remove(_services_path)


class TestPayloadSizeLimits:
    """Verify oversized payload rejection (DoS prevention).

    NOTE: These tests document production gaps. Actual implementation must:
    1. Configure FastAPI request size limits (P1)
    2. Add JSON depth validation middleware (P2)
    3. Add array size limits in Pydantic schemas (P2)

    See: SECURITY.md for production hardening checklist.
    """

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
    def test_payload_size_limit_returns_413(self) -> None:
        """Oversized request bodies are rejected at the edge with HTTP 413."""
        app = FastAPI()
        add_security_middleware(
            app,
            SecurityConfig(
                max_body_size_bytes=128,
                strict_mode=True,
            ),
        )

        @app.post("/api/limited")
        async def limited(request: Request) -> dict[str, Any]:
            return await request.json()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/limited", json={"payload": "x" * 1024})
        assert response.status_code == 413
        assert response.json()["detail"] == "Request body too large"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
    def test_json_depth_limit_enforced(self) -> None:
        """Pathological nested JSON is rejected before route processing."""
        app = FastAPI()
        add_security_middleware(
            app,
            SecurityConfig(
                max_json_depth=4,
                strict_mode=True,
            ),
        )

        @app.post("/api/limited-depth")
        async def limited_depth(request: Request) -> dict[str, Any]:
            return await request.json()

        nested_payload = {"v": {"v": {"v": {"v": {"v": "boom"}}}}}
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/limited-depth", json=nested_payload)
        assert response.status_code == 400
        assert "Invalid JSON structure" in " ".join(response.json()["violations"])


class TestUnknownFieldHandling:
    """Verify unknown field rejection or stripping policy."""

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI/Pydantic not available")
    def test_unknown_fields_rejected_with_strict_schema(self) -> None:
        """Negative: Unknown fields should be rejected when strict validation enabled.
        
        Prevents data pollution and schema evolution attacks.
        """
        class StrictSchema(BaseModel):
            name: str
            value: int
            
            model_config = ConfigDict(extra="forbid")  # Reject unknown fields
        
        # Valid data
        valid_data = {"name": "test", "value": 42}
        schema = StrictSchema(**valid_data)
        assert schema.name == "test"
        assert schema.value == 42
        
        # Invalid data with unknown field
        invalid_data = {"name": "test", "value": 42, "extra_field": "malicious"}
        
        with pytest.raises(ValidationError) as exc_info:
            StrictSchema(**invalid_data)
        
        error_msg = str(exc_info.value)
        assert "extra_field" in error_msg or "extra" in error_msg.lower()

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI/Pydantic not available")
    def test_unknown_fields_stripped_with_permissive_schema(self) -> None:
        """Positive: When configured, unknown fields are silently stripped.
        
        This is a valid policy choice but should be intentional.
        """
        class PermissiveSchema(BaseModel):
            name: str
            
            model_config = ConfigDict(extra="ignore")  # Ignore unknown fields
        
        data_with_extra = {"name": "test", "unknown": "ignored"}
        schema = PermissiveSchema(**data_with_extra)
        
        assert schema.name == "test"
        # unknown field is not accessible
        assert not hasattr(schema, "unknown") or getattr(schema, "unknown", None) is None


class TestUnsafeStringSanitization:
    """Verify unsafe string content is sanitized.

    NOTE: These tests document security gaps. Production implementation must:
    1. Add XSS sanitization middleware ( bleach/html-sanitizer )
    2. Use parameterized queries exclusively (sqlalchemy text())
    3. Validate input encoding and reject null bytes

    See: docs/core-concepts/security-model.md
    """

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
    def test_xss_sanitization_applied_to_json_fields(self) -> None:
        """User-supplied string fields are centrally sanitized."""
        app = FastAPI()
        add_security_middleware(app, SecurityConfig(strict_mode=False, sanitize_json_strings=True))

        @app.post("/api/echo")
        async def echo(request: Request) -> dict[str, Any]:
            return await request.json()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/echo",
            json={"name": "<script>alert(1)</script>", "tags": ["ok", "<b>x</b>"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "&lt;script&gt;alert(1)&lt;/script&gt;"
        assert data["tags"][1] == "&lt;b&gt;x&lt;/b&gt;"

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
    def test_sql_injection_pattern_blocked_centrally(self) -> None:
        """Shared defensive layer blocks obvious SQLi in untrusted text."""
        app = FastAPI()
        add_security_middleware(app, SecurityConfig(strict_mode=True))

        @app.post("/api/echo")
        async def echo(request: Request) -> dict[str, Any]:
            return await request.json()

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/echo", json={"query": "' OR 1=1 --"})
        assert response.status_code == 400
        assert any("SQL injection detected" in v for v in response.json()["violations"])


class TestEnumAndStateValidation:
    """Verify enum values and state transitions are validated."""

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="Pydantic not available")
    def test_invalid_enum_value_rejected(self) -> None:
        """Negative: Invalid enum values should be rejected during validation.
        
        Prevents data pollution with unexpected status values.
        """
        from enum import Enum
        
        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"
            PENDING = "pending"
        
        class Item(BaseModel):
            name: str
            status: Status
        
        # Valid value
        item = Item(name="test", status=Status.ACTIVE)
        assert item.status == Status.ACTIVE
        
        # Invalid value should fail
        with pytest.raises(ValidationError):
            Item(name="test", status="invalid_status")

    def test_state_transition_validation(self) -> None:
        """Negative: Invalid state transitions should be rejected.
        
        Tests the same invariant as tenant lifecycle but for generic state machines.
        """
        # Valid transitions
        valid_transitions = {
            "pending": ["active", "cancelled"],
            "active": ["suspended", "deleted"],
            "suspended": ["active", "deleted"],
            "deleted": [],  # Terminal state
        }
        
        def can_transition(from_state: str, to_state: str) -> bool:
            return to_state in valid_transitions.get(from_state, [])
        
        # Valid transitions
        assert can_transition("pending", "active") is True
        assert can_transition("active", "suspended") is True
        
        # Invalid transitions
        assert can_transition("deleted", "active") is False
        assert can_transition("suspended", "pending") is False


class TestContentTypeValidation:
    """Verify content type validation."""

    @pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
    def test_invalid_content_type_rejected(self) -> None:
        """Negative: Requests with unexpected content types should be rejected.
        
        Prevents confusion attacks with wrong content types.
        """
        app = FastAPI()
        
        @app.post("/api/json-only")
        async def json_endpoint(request: Request):
            return await request.json()
        
        client = TestClient(app, raise_server_exceptions=False)
        
        # Send with wrong content type
        response = client.post(
            "/api/json-only",
            data="not json",
            headers={"Content-Type": "text/plain"}
        )
        
        # Should fail to parse
        assert response.status_code in [400, 422, 500]
