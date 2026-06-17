---
title: "ADR-031: RequestContext Contract Definition"
category: "architecture"
audience: "advanced"
last-reviewed: "2026-05-25"
freshness: "current"
related: ["../../explanations/adr/ADR-004-jwt-api-key-authentication-strategy", "../../explanations/adr/ADR-010-postgresql-rls-for-multi-tenancy"]
---

# ADR-031: RequestContext Contract Definition

**Status:** ✅ Accepted

**Date:** 2026-05-25

**Deciders:** Platform Engineering, Security Team

---

## Context

`RequestContext` is the canonical shared identity contract used by all Fabric_4L layers (L1-L6). It carries tenant, user, auth-source, trace, isolation, and privileged-access fields required by governance middleware and security checks.

Recent test failures indicate contract drift between the runtime `RequestContext` model and test expectations:

- Tests expect `is_isolation_tier_valid()` method (missing from model)
- Tests expect `is_service_account()` method (missing from model)
- Tests expect `_uuid_to_str()` static helper (missing from model)
- Tests expect specific default behavior for `auth_source` field

The model currently has:
- `is_auth_source_valid()` method
- `validate()` method that returns errors
- `to_dict()` and `to_log_dict()` serialization methods
- Field-level validation in `__post_init__`

## Decision

### Canonical RequestContext Fields

**Required Fields:**
- `tenant_id: Optional[UUID | str]` - Tenant identifier (required for authenticated requests)
- `auth_source: str` - Authentication source (normalized in `__post_init__`)

**Optional Fields:**
- `user_id: Optional[Any]` - User identifier
- `org_id: Optional[Any]` - Organization identifier
- `workspace_id: Optional[Any]` - Workspace identifier
- `api_key_id: Optional[str]` - API key identifier
- `service_account_id: Optional[str]` - Service account identifier
- `tenant_role: Optional[str]` - Tenant role (e.g., "admin")
- `trace_id: Optional[str]` - Trace identifier
- `request_id: Optional[str]` - Request identifier
- `impersonator_id: Optional[str]` - Impersonator identifier
- `privileged_session_start: Optional[float]` - Privileged session start timestamp

**Collection Fields:**
- `roles: List[str]` - Role memberships
- `permissions: FrozenSet[Permission | str]` - Permission grants
- `service_account_scopes: List[str]` - Service account OAuth scopes
- `accessed_tenant_ids: Set[str]` - Tenant IDs accessed during session

**Governance Fields:**
- `isolation_tier: str` - Tenant isolation tier (shared/schema/database)
- `source: str` - Legacy auth source field (normalized in `__post_init__`)
- `raw: Dict[str, Any]` - Raw JWT/API key claims

**Internal Fields:**
- `_locked: bool` - Immutability guard (not part of public contract)

### Field Representation

**UUID Fields:**
- `tenant_id`, `user_id`, `org_id`, `workspace_id` accept both `UUID` and `str` types
- Serialization via `to_dict()` converts to `str` representation
- No `_uuid_to_str()` helper method - use inline `str()` conversion

**Auth Source Constants:**
- `AUTH_SOURCE_JWT = "jwt_claim"`
- `AUTH_SOURCE_API_KEY = "api_key"`
- `AUTH_SOURCE_SERVICE_ACCOUNT = "service_account"`
- `AUTH_SOURCE_UNKNOWN = "unknown"` (fallback for unauthenticated/legacy contexts, NOT in VALID_AUTH_SOURCES)

**Valid Auth Sources:**
- `VALID_AUTH_SOURCES = {AUTH_SOURCE_JWT, AUTH_SOURCE_API_KEY, AUTH_SOURCE_SERVICE_ACCOUNT}`
- `AUTH_SOURCE_UNKNOWN` is NOT in `VALID_AUTH_SOURCES` - it's a fallback value that fails `is_auth_source_valid()`

**Isolation Tier Constants:**
- `ISOLATION_TIER_SHARED = "shared"` (default)
- `ISOLATION_TIER_SCHEMA = "schema"`
- `ISOLATION_TIER_DATABASE = "database"`

### Service Account Behavior

**Detection:**
- Service account is identified by `service_account_id` field presence
- No `is_service_account()` method - use `ctx.service_account_id is not None`

**Validation:**
- When `auth_source == AUTH_SOURCE_SERVICE_ACCOUNT`:
  - `service_account_id` is required
  - `service_account_scopes` must be non-empty
- Enforced via `validate()` method

### Isolation Tier Validation

**Validation:**
- Isolation tier must be one of `VALID_ISOLATION_TIERS`
- No `is_isolation_tier_valid()` method - use `ctx.isolation_tier in VALID_ISOLATION_TIERS`
- Enforced via `validate()` method

### Serialization Behavior

**`to_dict()`:**
- Returns `Dict[str, Any]` with all non-secret fields
- UUID fields converted to `str`
- `None` values preserved as `None`
- Used for cross-layer contracts and API responses

**`to_log_dict()`:**
- Returns subset of fields for structured logging
- Excludes sensitive data (permissions, detailed roles)
- Uses `TypedDictModel` for schema validation

### Immutability

**Immutable Fields (protected after construction):**
- `tenant_id`
- `permissions`
- `workspace_id`

**Mutable Fields (for audit instrumentation):**
- `accessed_tenant_ids`
- `privileged_session_start`

Enforced via `__setattr__` override and `_locked` flag.

### Compatibility/Deprecation Policy

**Legacy Support:**
- `source` field maintained for backward compatibility
- Legacy auth source aliases normalized in `__post_init__`
- `get_current_context()` alias for `get_request_context()`

**Deprecation Path:**
- Tests asserting obsolete methods should be updated to use field checks
- No compatibility shims for `is_service_account()` or `is_isolation_tier_valid()`
- Direct field access is the canonical pattern

## Consequences

### Positive

- **Explicit contract:** Clear distinction between required vs optional fields
- **Type safety:** UUID fields accept both types for flexibility
- **Validation:** Centralized `validate()` method for fail-closed checks
- **Immutability:** Protected fields prevent escalation attacks
- **Serialization:** Stable `to_dict()` for cross-layer contracts

### Negative

- **Test updates required:** Tests expecting helper methods must be updated
- **No convenience methods:** Tests must use direct field access instead of `is_service_account()`
- **Learning curve:** New contributors must understand field-based validation

### Migration Path

1. **Update tests:**
   - Replace `ctx.is_service_account()` with `ctx.service_account_id is not None`
   - Replace `ctx.is_isolation_tier_valid()` with `ctx.isolation_tier in VALID_ISOLATION_TIERS`
   - Remove `RequestContext._uuid_to_str()` calls, use inline `str()`

2. **Add missing methods to model (if needed):**
   - `is_service_account()` - convenience method (optional)
   - `is_isolation_tier_valid()` - convenience method (optional)
   - Decision: Add as convenience methods for test compatibility

3. **Update documentation:**
   - This ADR becomes source of truth for RequestContext contract
   - Update inline docstrings to reference this ADR

## Implementation

**Model Updates:**
- Add `is_service_account()` convenience method
- Add `is_isolation_tier_valid()` convenience method
- Do NOT add `_uuid_to_str()` - use inline `str()` conversion

**Test Updates:**
- Update `test_request_context_defaults` to expect `AUTH_SOURCE_UNKNOWN` as default
- Update `test_uuid_to_str_helper` to be removed (obsolete test)
- Keep convenience method tests for backward compatibility

**Status Codes:**
- 401 = no valid authentication
- 403 = authenticated but not authorized
- 400 = tenant_id missing or invalid request structure
- 404 = resource not found or intentionally hidden

## References

- ADR-004: JWT + API Key Authentication Strategy
- ADR-010: PostgreSQL RLS for Multi-Tenancy
- `packages/shared/src/value_fabric/shared/identity/context.py`
