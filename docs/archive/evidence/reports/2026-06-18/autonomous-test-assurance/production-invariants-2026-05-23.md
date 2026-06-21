# Production Invariants

Generated: 2026-05-23

## Tenant Isolation
- **Rule**: No cross-tenant reads or writes
- **Enforcement**: RLS policies, JWT claim validation, middleware
- **Code**: `services/layer3-knowledge/src/auth/middleware.py`, `services/layer4-agents/src/tenants/...`

## Authentication
- **Rule**: No unauthenticated access to protected resources
- **Enforcement**: `get_current_api_key`, `require_authenticated`, `AuthenticationMiddleware`
- **Code**: `services/layer3-knowledge/src/auth/middleware.py:97-155`

## Authorization
- **Rule**: Role/permission checks before data access
- **Enforcement**: `require_permission`, RBAC middleware
- **Code**: `services/layer3-knowledge/src/auth/middleware.py:179-199`

## Input Validation
- **Rule**: No unvalidated input reaches persistence or LLM calls
- **Enforcement**: Pydantic schemas, regex validators
- **Code**: Route handlers across all layers

## RLS Enforcement
- **Rule**: DB queries scoped to tenant_id
- **Enforcement**: `SET LOCAL app.tenant_id`, RLS policies in migrations
- **Code**: `services/*/migrations/*rls*`, `services/layer4-agents/src/database.py`
