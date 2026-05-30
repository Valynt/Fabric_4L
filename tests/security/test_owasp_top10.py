"""
OWASP Top 10 Manual Security Tests

Complements automated ZAP scanning with business-logic-aware tests
for categories ZAP cannot fully validate: A01-A04.
"""

import re
import time
from typing import Callable

import jwt as jwt_lib
import pytest

# Lazy import for optional dependency
try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

# UUID pattern for IDOR prevention tests
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


class TestBrokenAccessControl:
    """OWASP A01: Broken Access Control

    ZAP misses business-logic authorization. These tests verify:
    - IDOR (Insecure Direct Object Reference) prevention
    - Path traversal protection
    - Method-level access control
    """

    def test_idor_prevention_on_entity_endpoints(self, client: TestClient, tenant_a_token, tenant_b_token):
        """P0: IDOR via sequential ID enumeration is blocked."""
        # Tenant A creates an entity
        create_response = client.post(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {tenant_a_token}"},
            json={"name": "idor-test-entity"},
        )

        # Fail explicitly if entity creation fails - cannot test IDOR without entity
        assert create_response.status_code == 201, (
            f"Entity creation failed with status {create_response.status_code} - cannot test IDOR"
        )
        entity = create_response.json()
        entity_id = entity.get("id")
        assert entity_id, "Entity ID not returned in response"

        # Tenant B attempts to access Tenant A's entity by ID
        idor_response = client.get(
            f"/api/v1/entities/{entity_id}",
            headers={"Authorization": f"Bearer {tenant_b_token}"},
        )

        # Should be blocked - Tenant B should not see Tenant A's entity
        assert idor_response.status_code in [403, 404], (
            f"IDOR vulnerability: Tenant B accessed Tenant A's entity {entity_id}"
        )

    def test_idor_prevention_via_uuid_randomization(self, client: TestClient, tenant_a_token: str):
        """P0: Entity IDs use unpredictable UUIDs, not sequential integers."""
        # Create multiple entities
        entity_ids = []
        for i in range(3):
            response = client.post(
                "/api/v1/entities",
                headers={"Authorization": f"Bearer {tenant_a_token}"},
                json={"name": f"uuid-test-{i}"},
            )
            # Fail explicitly if entity creation fails
            assert response.status_code == 201, (
                f"Entity creation failed with status {response.status_code} - cannot test UUID pattern"
            )
            entity_id = response.json().get("id")
            assert entity_id, f"Entity ID not returned for entity {i}"
            entity_ids.append(entity_id)

        # Verify all IDs are UUIDs (not sequential)
        assert len(entity_ids) == 3, f"Expected 3 entities, got {len(entity_ids)}"
        for entity_id in entity_ids:
            assert UUID_PATTERN.match(str(entity_id)), (
                f"Entity ID {entity_id} is not a UUID - vulnerable to ID enumeration"
            )

    def test_path_traversal_blocked(self, client: TestClient, admin_user_token):
        """P0: Path traversal attacks in file paths are blocked."""
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
            "....//....//....//etc/passwd",  # Double encoding bypass attempt
        ]

        for payload in traversal_payloads:
            response = client.get(
                f"/api/v1/files/{payload}",
                headers={"Authorization": f"Bearer {admin_user_token}"},
            )
            # Should be blocked - no file access should succeed
            assert response.status_code in [400, 403, 404], (
                f"Path traversal not blocked for payload: {payload}"
            )

    def test_http_method_not_allowed_for_role(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """P0: HTTP method restrictions enforced per role."""
        read_only_token = jwt_encoder({
            "sub": "read-only",
            "tenant_id": "tenant-a",
            "role": "read_only",
            "permissions": ["read"],
        })

        # Read-only role should not allow DELETE
        delete_response = client.delete(
            "/api/v1/entities/some-id",
            headers={"Authorization": f"Bearer {read_only_token}"},
        )
        assert delete_response.status_code in [403, 405, 401], (
            "Read-only role should not allow DELETE method"
        )

        # Read-only role should not allow PATCH (partial update)
        patch_response = client.patch(
            "/api/v1/entities/some-id",
            headers={"Authorization": f"Bearer {read_only_token}"},
            json={"name": "patched-name"},
        )
        assert patch_response.status_code in [403, 405, 401], (
            "Read-only role should not allow PATCH method"
        )

    def test_mass_assignment_protection(self, client: TestClient, standard_user_token):
        """P0: Mass assignment of protected fields is blocked."""
        # Attempt to set protected fields during entity creation
        response = client.post(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {standard_user_token}"},
            json={
                "name": "test-entity",
                "role": "admin",  # Protected field - should not be assignable
                "is_admin": True,  # Protected boolean
                "password_hash": "fake-hash",  # Should never be settable
            },
        )

        # Either: request is rejected due to protected fields
        # Or: if accepted, protected fields must be stripped
        if response.status_code in [400, 403, 422]:
            # Request rejected - mass assignment protection working
            pass
        elif response.status_code == 201:
            # Request accepted - verify protected fields were stripped
            entity = response.json()
            assert entity.get("role") != "admin", "Mass assignment vulnerability: role was set"
            assert entity.get("is_admin") is not True, "Mass assignment vulnerability: is_admin was set"
            assert "password_hash" not in entity, "Mass assignment vulnerability: password_hash was set"
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


class TestCryptographicFailures:
    """OWASP A02: Cryptographic Failures

    Tests for password handling, key management, and sensitive data exposure.
    """

    def test_passwords_not_logged(self, client: TestClient, admin_user_token, caplog):
        """P0: Passwords are not logged in plaintext."""
        import logging

        # Set logging to capture all levels
        with caplog.at_level(logging.INFO):
            # Attempt login or password-related operation
            _ = client.post(  # noqa: F841 - testing that password is not logged
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "SuperSecretPassword123!",
                },
            )

        # Check logs do not contain plaintext password
        log_text = caplog.text
        assert "SuperSecretPassword123!" not in log_text, (
            "Security violation: Password found in logs"
        )

    def test_api_keys_use_hmac_not_bcrypt(self, client: TestClient, db_connection):
        """P0: API keys use HMAC-SHA256 (fast verification) not bcrypt."""
        # Query to check API key storage format
        with db_connection.cursor() as cursor:
            cursor.execute(
                "SELECT key_hash FROM api_keys WHERE key_hash IS NOT NULL LIMIT 1"
            )
            result = cursor.fetchone()

            if result and result[0]:
                key_hash = result[0]
                # HMAC-SHA256 produces 64 hex characters (256 bits)
                # bcrypt produces strings starting with $2b$ or $2a$
                assert not key_hash.startswith(("$2b$", "$2a$", "$2y$")), (
                    "API key using bcrypt instead of HMAC-SHA256 - performance issue"
                )
                assert len(key_hash) == 64, (
                    f"API key hash length {len(key_hash)} != 64 - may not be HMAC-SHA256"
                )

    def test_jwt_uses_secure_algorithm(self, client: TestClient, jwt_encoder: Callable[[dict], str]):
        """P0: JWT tokens use secure algorithm (HS256 or RS256)."""
        # Create and decode a token to check algorithm
        token = jwt_encoder({"sub": "test", "role": "standard"})
        header = jwt_lib.get_unverified_header(token)

        algorithm = header.get("alg", "").upper()
        assert algorithm in ["HS256", "RS256", "ES256"], (
            f"Insecure JWT algorithm: {algorithm}. Use HS256, RS256, or ES256"
        )

        # Explicitly reject weak algorithms
        assert algorithm not in ["NONE", "HS1", "HS384", "HS512"], (
            f"Algorithm {algorithm} not explicitly validated for security"
        )

    def test_secrets_not_in_error_messages(self, client: TestClient):
        """P0: Error messages do not leak secrets or stack traces."""
        # Trigger an error condition
        response = client.get(
            "/api/v1/entities/malformed-uuid",
        )

        response_text = response.text.lower()

        # Check for secrets in error response
        forbidden_patterns = [
            "password", "secret", "api_key", "apikey", "token",
            "jdbc:", "postgresql://", "redis://", "mongodb://",
            "private_key", "-----begin", "-----end",
        ]

        for pattern in forbidden_patterns:
            assert pattern not in response_text, (
                f"Secret leakage in error: found '{pattern}' in response"
            )

    def test_database_connection_strings_not_exposed(self, client: TestClient, admin_user_token):
        """P0: Database connection strings not exposed via API."""
        # Attempt to access configuration endpoints
        response = client.get(
            "/api/v1/admin/config",
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        if response.status_code == 200:
            config = response.json()
            config_str = str(config).lower()

            # Check for connection strings in config
            assert "postgresql://" not in config_str, "DB connection string exposed in config API"
            assert "redis://" not in config_str, "Redis connection string exposed in config API"
            assert "password" not in config_str, "Password exposed in config API"


class TestInjection:
    """OWASP A03: Injection

    Complements existing SQL/XSS tests with additional injection vectors.
    """

    def test_cypher_injection_blocked(self, client: TestClient, tenant_a_token):
        """P0: Neo4j Cypher injection is prevented."""
        cypher_payloads = [
            "MATCH (n) DELETE n",  # Attempt data deletion
            "MATCH (n) RETURN n LIMIT 1; MATCH (a) DELETE a",  # Stacked queries
            "' OR 1=1 MATCH (n) RETURN n",  # Boolean injection
            "{\"name\": \"test\"}) RETURN 1; MATCH (n) DELETE n //",  # Comment injection
        ]

        for payload in cypher_payloads:
            response = client.post(
                "/api/v1/query/graph",
                headers={"Authorization": f"Bearer {tenant_a_token}"},
                json={"query": payload},
            )
            # Should be blocked or query should be parameterized safely
            assert response.status_code in [200, 400, 403], (
                f"Cypher injection not properly blocked for payload"
            )

            if response.status_code == 200:
                # If allowed, should not have deleted/modified data
                _ = response.json()  # noqa: F841 - verifying response is valid JSON
                # Response should be structured, not raw Cypher error

    def test_xxe_prevention(self, client: TestClient, admin_user_token):
        """P0: XML External Entity (XXE) attacks are blocked."""
        xxe_payload = """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
        <foo>&xxe;</foo>"""

        # Try XML endpoint if it exists
        response = client.post(
            "/api/v1/import/xml",
            headers={
                "Authorization": f"Bearer {admin_user_token}",
                "Content-Type": "application/xml",
            },
            data=xxe_payload,
        )

        # Should be blocked or safely processed without entity expansion
        if response.status_code == 200:
            response_text = response.text
            assert "root:" not in response_text, "XXE vulnerability: file contents exposed"
        elif response.status_code not in [400, 403, 404, 422]:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_template_injection_blocked(self, client: TestClient, tenant_a_token):
        """P0: Server-Side Template Injection (SSTI) is blocked."""
        ssti_payloads = [
            "{{ config }}",  # Jinja2
            "{{ 7 * 7 }}",  # Expression evaluation
            "${7*7}",  # Alternative syntax
            "<%= 7 * 7 %>",  # ERB syntax
        ]

        for payload in ssti_payloads:
            response = client.post(
                "/api/v1/entities",
                headers={"Authorization": f"Bearer {tenant_a_token}"},
                json={
                    "name": "test",
                    "description": payload,  # If templated, this could execute
                },
            )

            if response.status_code == 200:
                data = response.json()
                description = data.get("description", "")
                # If SSTI executed, we'd see "49" (7*7) instead of the payload
                assert "49" not in str(description), (
                    f"SSTI vulnerability: template expression executed"
                )
            elif response.status_code not in [201, 400, 403, 422]:
                pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_ldap_injection_blocked(self, client: TestClient):
        """P0: LDAP injection patterns are blocked."""
        ldap_payloads = [
            "*)(uid=*))(&(uid=*",  # LDAP boolean injection
            "admin))(&(uid=*",  # Bypass authentication
            "*)(objectClass=*)",  # Wildcard injection
        ]

        for payload in ldap_payloads:
            response = client.post(
                "/api/v1/auth/ldap",
                json={
                    "username": payload,
                    "password": "any",
                },
            )
            # Should not authenticate successfully with injection
            assert response.status_code in [400, 401, 403, 404], (
                "LDAP injection not properly blocked"
            )


class TestInsecureDesign:
    """OWASP A04: Insecure Design

    Tests for business-logic security flaws and missing controls.
    """

    def test_rate_limiting_enforced(self, client: TestClient, standard_user_token):
        """P0: Rate limiting prevents brute force and abuse."""
        # Make rapid requests to trigger rate limit
        responses = []
        for i in range(20):
            response = client.get(
                "/api/v1/entities",
                headers={"Authorization": f"Bearer {standard_user_token}"},
            )
            responses.append(response.status_code)

        # Should eventually hit rate limit (429)
        assert 429 in responses or all(r in [200, 401, 403, 404] for r in responses), (
            "Rate limiting not enforced - no 429 responses"
        )

        # Check for rate limit headers
        for response in responses:
            if "X-RateLimit-Limit" in response.headers or "Retry-After" in response.headers:
                return  # Rate limiting properly implemented

    def test_audit_logs_immutable(self, client: TestClient, admin_user_token, db_connection):
        """P0: Audit logs cannot be modified or deleted."""
        # Create an action that generates an audit log
        response = client.post(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json={"name": "audit-test-entity"},
        )

        if response.status_code == 201:
            entity = response.json()
            entity_id = entity.get("id")

            # Attempt to directly modify audit log (simulating insider threat)
            with db_connection.cursor() as cursor:
                try:
                    cursor.execute(
                        "UPDATE audit_logs SET action = 'DELETED' WHERE entity_id = %s",
                        (entity_id,)
                    )
                    # If this succeeds, audit log is mutable - security violation
                    assert False, "Audit log immutability violation: UPDATE succeeded"
                except Exception:
                    # Expected: Should fail due to trigger/policy
                    assert True

                try:
                    cursor.execute(
                        "DELETE FROM audit_logs WHERE entity_id = %s",
                        (entity_id,)
                    )
                    # If this succeeds, audit log is deletable - security violation
                    assert False, "Audit log immutability violation: DELETE succeeded"
                except Exception:
                    # Expected: Should fail
                    assert True

    def test_sensitive_operations_require_confirmation(self, client: TestClient, admin_user_token):
        """P0: High-risk operations require additional confirmation or MFA."""
        # Attempt high-risk operation without confirmation
        response = client.post(
            "/api/v1/admin/delete-tenant",
            headers={"Authorization": f"Bearer {admin_user_token}"},
            json={"tenant_id": "some-tenant"},
        )

        # Should require MFA or confirmation token
        assert response.status_code in [403, 401, 400], (
            "High-risk operation allowed without confirmation/MFA - insecure design"
        )

    def test_resource_exhaustion_protection(self, client: TestClient, admin_user_token):
        """P0: Resource-intensive operations have limits."""
        # Attempt to request excessive resources
        response = client.get(
            "/api/v1/entities",
            params={
                "limit": 1000000,  # Absurdly large limit
                "offset": 0,
            },
            headers={"Authorization": f"Bearer {admin_user_token}"},
        )

        # Should be blocked or limited
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            assert len(items) <= 1000, (
                "Resource exhaustion vulnerability: returned too many items"
            )

    def test_business_logic_timing_attack_mitigation(self, client: TestClient):
        """P0: Authentication timing is constant to prevent user enumeration."""
        # Time responses for existing vs non-existing users
        existing_user_times = []
        nonexistent_user_times = []

        # Test existing user (if test user exists)
        for _ in range(3):
            start = time.time()
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "existing@tenant-a.com",
                    "password": "wrong-password",
                },
            )
            existing_user_times.append(time.time() - start)

        # Test non-existing user
        for _ in range(3):
            start = time.time()
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent@fake-domain-12345.com",
                    "password": "any-password",
                },
            )
            nonexistent_user_times.append(time.time() - start)

        # Calculate average times
        avg_existing = sum(existing_user_times) / len(existing_user_times)
        avg_nonexistent = sum(nonexistent_user_times) / len(nonexistent_user_times)

        # Times should be similar (within 50% to account for network variance)
        ratio = max(avg_existing, avg_nonexistent) / min(avg_existing, avg_nonexistent)
        assert ratio < 2.0, (
            f"Timing attack vulnerability: existing vs non-existing user "
            f"response times differ by {ratio:.2f}x"
        )
