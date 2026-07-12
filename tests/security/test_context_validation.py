"""Context Validation Security Tests — P1 Gap Remediation

Validates that RequestContext rejects invalid isolation tiers and invalid auth
sources at construction time, ensuring the identity contract fails closed rather
than silently accepting misconfigured contexts.

Gap matrix refs:
  P1 gap 1 — Invalid Isolation Tier: invalid tier value accepted
  P1 gap 2 — Invalid Auth Source: unknown auth source accepted

Author: Platform Security Team
"""

from __future__ import annotations

import pytest
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_API_KEY,
    AUTH_SOURCE_JWT,
    AUTH_SOURCE_SERVICE_ACCOUNT,
    AUTH_SOURCE_UNKNOWN,
    ISOLATION_TIER_DATABASE,
    ISOLATION_TIER_SCHEMA,
    ISOLATION_TIER_SHARED,
    VALID_AUTH_SOURCES,
    VALID_ISOLATION_TIERS,
    RequestContext,
)

pytestmark = [
    pytest.mark.security,
    pytest.mark.context_validation,
]

VALID_TENANT = "tenant-abc-123"


# ---------------------------------------------------------------------------
# Isolation Tier Validation
# ---------------------------------------------------------------------------


class TestIsolationTierValidation:
    """P1 gap 1: Invalid isolation tier values must be rejected by validate()."""

    def test_valid_shared_tier_accepted(self):
        """POSITIVE: 'shared' isolation tier is valid."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_JWT,
            isolation_tier=ISOLATION_TIER_SHARED,
        )
        errors = ctx.validate()
        tier_errors = [e for e in errors if "isolation_tier" in e]
        assert not tier_errors, f"Valid tier 'shared' should not produce errors: {tier_errors}"

    def test_valid_schema_tier_accepted(self):
        """POSITIVE: 'schema' isolation tier is valid."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_JWT,
            isolation_tier=ISOLATION_TIER_SCHEMA,
        )
        errors = ctx.validate()
        tier_errors = [e for e in errors if "isolation_tier" in e]
        assert not tier_errors, f"Valid tier 'schema' should not produce errors: {tier_errors}"

    def test_valid_database_tier_accepted(self):
        """POSITIVE: 'database' isolation tier is valid."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_JWT,
            isolation_tier=ISOLATION_TIER_DATABASE,
        )
        errors = ctx.validate()
        tier_errors = [e for e in errors if "isolation_tier" in e]
        assert not tier_errors, f"Valid tier 'database' should not produce errors: {tier_errors}"

    def test_invalid_tier_rejected(self):
        """NEGATIVE: An unrecognised isolation tier produces a validation error."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_JWT,
            isolation_tier="superuser",
        )
        errors = ctx.validate()
        assert any("isolation_tier" in e for e in errors), (
            f"Invalid tier 'superuser' must produce an isolation_tier error. Got: {errors}"
        )

    def test_empty_tier_rejected(self):
        """NEGATIVE: Empty string isolation tier is invalid."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_JWT,
            isolation_tier="",
        )
        errors = ctx.validate()
        assert any("isolation_tier" in e for e in errors), (
            f"Empty isolation_tier must produce a validation error. Got: {errors}"
        )

    def test_uppercase_tier_rejected(self):
        """ADVERSARIAL: Case-variant of a valid tier is not accepted."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_JWT,
            isolation_tier="SHARED",
        )
        errors = ctx.validate()
        assert any("isolation_tier" in e for e in errors), (
            "Uppercase 'SHARED' must not be accepted as a valid isolation tier."
        )

    def test_all_valid_tiers_are_accepted(self):
        """POSITIVE: Every member of VALID_ISOLATION_TIERS passes validation."""
        for tier in VALID_ISOLATION_TIERS:
            ctx = RequestContext(
                tenant_id=VALID_TENANT,
                auth_source=AUTH_SOURCE_JWT,
                isolation_tier=tier,
            )
            errors = ctx.validate()
            tier_errors = [e for e in errors if "isolation_tier" in e]
            assert not tier_errors, f"Tier '{tier}' from VALID_ISOLATION_TIERS should be accepted. Got: {tier_errors}"


# ---------------------------------------------------------------------------
# Auth Source Validation
# ---------------------------------------------------------------------------


class TestAuthSourceValidation:
    """P1 gap 2: AUTH_SOURCE_UNKNOWN and unrecognised sources must be rejected."""

    def test_jwt_auth_source_valid(self):
        """POSITIVE: jwt_claim auth source is accepted."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_JWT,
        )
        errors = ctx.validate()
        auth_errors = [e for e in errors if "auth_source" in e]
        assert not auth_errors, f"jwt_claim auth source should be valid. Got: {auth_errors}"

    def test_api_key_auth_source_valid(self):
        """POSITIVE: api_key auth source is accepted."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_API_KEY,
        )
        errors = ctx.validate()
        auth_errors = [e for e in errors if "auth_source" in e]
        assert not auth_errors, f"api_key auth source should be valid. Got: {auth_errors}"

    def test_service_account_auth_source_valid_with_scopes(self):
        """POSITIVE: service_account auth source is accepted when scopes are present."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_SERVICE_ACCOUNT,
            service_account_id="svc-001",
            service_account_scopes=["read:entities"],
        )
        errors = ctx.validate()
        auth_errors = [e for e in errors if "auth_source" in e]
        assert not auth_errors, f"service_account auth source with scopes should be valid. Got: {auth_errors}"

    def test_unknown_auth_source_rejected(self):
        """NEGATIVE: AUTH_SOURCE_UNKNOWN must produce a validation error."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_UNKNOWN,
        )
        errors = ctx.validate()
        assert any("auth_source" in e for e in errors), (
            f"AUTH_SOURCE_UNKNOWN must produce an auth_source validation error. Got: {errors}"
        )

    def test_arbitrary_auth_source_rejected(self):
        """NEGATIVE: An unrecognised auth source string is rejected."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source="magic_token",
        )
        errors = ctx.validate()
        assert any("auth_source" in e for e in errors), (
            f"Unrecognised auth source 'magic_token' must be rejected. Got: {errors}"
        )

    def test_is_auth_source_valid_returns_false_for_unknown(self):
        """NEGATIVE: is_auth_source_valid() returns False for AUTH_SOURCE_UNKNOWN."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=AUTH_SOURCE_UNKNOWN,
        )
        assert not ctx.is_auth_source_valid(), (
            "is_auth_source_valid() must return False for AUTH_SOURCE_UNKNOWN"
        )

    def test_is_auth_source_valid_returns_true_for_all_valid_sources(self):
        """POSITIVE: is_auth_source_valid() returns True for every VALID_AUTH_SOURCES member."""
        for source in VALID_AUTH_SOURCES:
            extra = {}
            if source == AUTH_SOURCE_SERVICE_ACCOUNT:
                extra = {"service_account_id": "svc-x", "service_account_scopes": ["read:health"]}
            ctx = RequestContext(tenant_id=VALID_TENANT, auth_source=source, **extra)
            assert ctx.is_auth_source_valid(), (
                f"is_auth_source_valid() must return True for '{source}'"
            )

    def test_none_auth_source_falls_back_to_source_field(self):
        """ADVERSARIAL: None auth_source falls back to the 'source' field default (jwt_claim).

        When auth_source=None, __post_init__ uses self.source as the fallback.
        The default source is AUTH_SOURCE_JWT, so the context is valid.
        To get AUTH_SOURCE_UNKNOWN, both auth_source and source must be unknown/empty.
        """
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=None,
            # source defaults to AUTH_SOURCE_JWT
        )
        # auth_source is normalised from source (jwt_claim), not to unknown
        assert ctx.auth_source == AUTH_SOURCE_JWT, (
            f"None auth_source with default source should normalise to '{AUTH_SOURCE_JWT}', "
            f"got '{ctx.auth_source}'"
        )
        # The context is valid because the fallback source is jwt_claim
        errors = ctx.validate()
        auth_errors = [e for e in errors if "auth_source" in e]
        assert not auth_errors, (
            f"None auth_source with valid source fallback should not produce auth_source errors. "
            f"Got: {auth_errors}"
        )

    def test_none_auth_source_with_unknown_source_is_rejected(self):
        """ADVERSARIAL: None auth_source with source=unknown produces a validation error."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source=None,
            source=AUTH_SOURCE_UNKNOWN,
        )
        # Both auth_source and source are unknown — validation must fail
        errors = ctx.validate()
        assert any("auth_source" in e for e in errors), (
            f"None auth_source with source=unknown must fail validation. Got: {errors}"
        )

    def test_injection_in_auth_source_rejected(self):
        """ADVERSARIAL: Injection attempt in auth_source is not accepted as valid."""
        ctx = RequestContext(
            tenant_id=VALID_TENANT,
            auth_source="jwt_claim; DROP TABLE tenants;",
        )
        errors = ctx.validate()
        assert any("auth_source" in e for e in errors), (
            "Injection string in auth_source must be rejected by validation."
        )
