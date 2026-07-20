# Tenant Management Security Remediation Plan

This document outlines the detailed remediation steps for the 6 security vulnerabilities identified during the cold-eye security audit of the Phase 1-3 tenant management code.

## 1. Critical: Auth Boundary Bypass
**Location:** `shared/identity/dependencies.py:41`
**Issue:** `require_authenticated()` only checks if `tenant_id` or `user_id` is present on the `RequestContext`. It does not verify a token, signature, or session.
**Remediation:**
- Update `require_authenticated()` to verify that the `auth_source` on the `RequestContext` is valid (e.g., `jwt_claim`, `api_key`, or `service_account`) and not `unknown`.
- Ensure that `GovernanceMiddleware` explicitly sets `auth_source="unknown"` if no valid authentication is provided, rather than just leaving the context empty.
- **Code Change:**
  ```python
  if not context.tenant_id and not context.user_id:
      raise HTTPException(status_code=401, detail="Authentication required")
  if context.auth_source == "unknown":
      raise HTTPException(status_code=401, detail="Valid authentication token required")
  ```

## 2. Critical: SQL Injection & JSON Corruption
**Location:** `services/layer4-agents/src/tenants/api/routes/admin_dashboard.py:405`
**Issue:** In `PATCH /settings`, the code dynamically constructs a `SET` clause and serializes the JSON settings dict using naive string replacement `str(updates['settings']).replace("'", '"')`.
**Remediation:**
- Replace the naive string replacement with proper JSON serialization using Python's built-in `json` module.
- **Code Change:**
  ```python
  import json
  # ...
  if "settings" in updates:
      set_parts.append("settings = :settings::jsonb")
      params["settings"] = json.dumps(updates["settings"])
  ```

## 3. High: Silent Provisioning Failure
**Location:** `services/layer4-agents/src/tenants/provisioning.py:172`
**Issue:** Audit emitter signature mismatch. `emit_audit_event()` requires `outcome` and `resource_type` parameters, but the provisioning service calls it without them.
**Remediation:**
- Update all 6 calls to `emit_audit_event()` in `provisioning.py` to include the required `outcome` and `resource_type` parameters.
- **Code Change:**
  ```python
  await emit_audit_event(
      action=AuditAction.TENANT_PROVISIONED,
      outcome=AuditOutcome.SUCCESS,
      resource_type="tenant",
      tenant_id=tenant_id,
      # ...
  )
  ```

## 4. High: Privilege Escalation via API Keys
**Location:** `shared/identity/models.py:APIKeyCreateRequest` and `api_keys.py`
**Issue:** `APIKeyCreateRequest` accepts an arbitrary `permissions: list[str]` field with no validation.
**Remediation:**
- Add a Pydantic validator to `APIKeyCreateRequest` to restrict permissions to a predefined allowlist of safe API scopes (e.g., `api:read`, `api:write`).
- In the route handler, intersect the requested permissions with the caller's actual permissions to ensure they cannot grant permissions they do not possess.
- **Code Change:**
  ```python
  # In models.py
  ALLOWED_API_SCOPES = {"api:read", "api:write", "agent:execute"}

  @field_validator("permissions")
  @classmethod
  def validate_permissions(cls, v: list[str] | None) -> list[str] | None:
      if v is not None:
          invalid = set(v) - cls.ALLOWED_API_SCOPES
          if invalid:
              raise ValueError(f"Invalid API scopes: {invalid}")
      return v
  ```

## 5. Medium: Runtime Crash on Privileged Access
**Location:** `shared/identity/context.py:28` and `dependencies.py:149`
**Issue:** `RequestContext` is declared as `@dataclass(frozen=True)`, but `dependencies.py` attempts to mutate it.
**Remediation:**
- Remove `frozen=True` from the `RequestContext` dataclass definition to allow the necessary session-tracking mutations.
- **Code Change:**
  ```python
  @dataclass
  class RequestContext:
      # ...
  ```

## 6. Medium: Potential SQL Injection via f-string
**Location:** `services/layer4-agents/src/tenants/usage_tracking.py:309`
**Issue:** In `_count_events_by_field`, the `group_field` parameter is interpolated directly into the SQL string via an f-string.
**Remediation:**
- Add an allowlist validation for the `group_field` parameter before interpolating it into the SQL query.
- **Code Change:**
  ```python
  ALLOWED_GROUP_FIELDS = {"resource_type", "action", "outcome"}
  if group_field not in ALLOWED_GROUP_FIELDS:
      raise ValueError(f"Invalid group_field: {group_field}")
  ```

## Execution Plan
1. Implement fixes for Findings 2, 3, 5, and 6 (straightforward code changes).
2. Implement fix for Finding 4 (requires model and route updates).
3. Implement fix for Finding 1 (requires careful testing of auth flows).
4. Run the full test suite to ensure no regressions.
5. Commit and push the remediation patch.
