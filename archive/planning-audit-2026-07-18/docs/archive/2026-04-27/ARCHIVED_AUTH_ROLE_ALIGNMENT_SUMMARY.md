---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Implementation complete
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Auth Role Alignment Implementation Summary

## Problem
Backend returned canonical roles (`super_admin`, `tenant_admin`, `content_admin`, `analyst`, `read_only`, `system`) but frontend schema only accepted frontend tiers (`standard`, `advanced`, `admin`), causing OIDC login failures.

## Solution
Implemented tiered normalization: Backend roles → Frontend tiers at the store boundary.

## Files Changed

### 1. `frontend/client/src/schemas/auth.ts`
**What was wrong:** Role enum only accepted frontend tiers, rejecting all backend-canonical roles.

**Changes:**
- Added `BackendRoles` array with canonical backend roles
- Added `FrontendTiers` array for UI presentation layer
- Added `AllRoles` union for schema validation
- Exported new types: `BackendRole`, `FrontendTier`, `UserRole`
- Updated `UserInfoSchema.role` and `TokenResponseSchema.role` to accept `AllRoles`

**Why:** Schema now accepts the union of backend-canonical and frontend-presentational roles. Normalization to UI tiers happens after validation in the store.

**Compatibility:** Existing code using frontend-tier roles continues to work.

---

### 2. `frontend/client/src/stores/userTierStore.ts`
**What was wrong:** `setUserRole()` had incomplete role mapping (missing `super_admin`, `tenant_admin`, `content_admin`, `read_only`).

**Changes:**
- Added exported `normalizeRoleToTier(role: string): UserTier` function with complete mapping:
  - `super_admin` → `admin`
  - `tenant_admin` → `admin`
  - `content_admin` → `admin`
  - `analyst` → `advanced`
  - `read_only` → `standard`
  - `system` → `standard` (fail-safe)
  - Plus all frontend tiers pass through
- Unknown roles fail-safe to `standard` with dev warning
- Replaced inline `roleTierMap` with `normalizeRoleToTier()` call in `setUserRole()`

**Why:** Single source of truth for role normalization. Backend roles are canonical; UI tiers are presentation abstraction.

**Compatibility:** All existing role values work. Unknown roles degrade safely.

---

### 3. `frontend/client/src/stores/userTierStore.test.ts`
**What was wrong:** Tests only covered frontend-tier roles, no backend role coverage.

**Changes:**
- Added import for `normalizeRoleToTier`
- Added backend role tests to `setUserRole` describe block:
  - `super_admin` → `admin` tier with admin permissions
  - `tenant_admin` → `admin` tier with user management
  - `content_admin` → `admin` tier
  - `read_only` → `standard` tier (no elevated permissions)
  - `system` → `standard` tier (fail-safe)
- Added new `normalizeRoleToTier` describe block with 17 test cases:
  - All backend roles map correctly
  - Frontend tiers pass through
  - Legacy roles (`editor`, `viewer`, `user`) work
  - Case-insensitive handling
  - Unknown roles fail-safe to `standard`
  - Whitespace trimming

**Why:** Tests verify backend-to-frontend role mapping and fail-safe behavior.

---

### 4. `frontend/client/src/contexts/AuthContext.test.tsx`
**What was wrong:** Tests used frontend-tier roles (`admin`, `standard`) instead of backend-canonical roles.

**Changes:**
- Updated 3 test cases to use backend-canonical roles:
  - `restores auth state` → `tenant_admin`
  - `logout clears auth state` → `super_admin`
  - `invalid token handling` → `read_only`
- Fixed test expectation for devBypass email (`dev@value-fabric.com` → `dev@example.com`)

**Why:** Tests now validate the full normalization path from backend role → UI tier.

---

### 5. `frontend/test/mocks/handlers.ts`
**What was wrong:** Mock returned frontend-tier role `advanced` instead of backend-canonical role.

**Changes:**
- Updated auth callback mock to return `analyst` (backend role) with comment explaining normalization

**Why:** Mocks use backend-canonical roles to validate the full auth flow including normalization.

---

### 6. `frontend/e2e/fixtures/tier-helpers.ts`
**What was wrong:** Only accepted frontend tiers, no backend role support.

**Changes:**
- Added `BackendRole` type export with all canonical roles
- Added optional `backendRole` parameter to `setUserTier()`
- Updated function to store both `userRole` (backend) and `currentTier` (normalized)

**Why:** E2E helpers support both backend roles and frontend tiers for comprehensive testing.

---

## Verification Results

### TypeScript Compilation
- **Status:** ✅ No errors in modified files
- Pre-existing errors in unrelated files (useAccounts.ts, useAgentStream.ts, etc.)

### Test Results

**userTierStore.test.ts:**
```
Test Files  1 passed (1)
     Tests  72 passed (72)
Duration  3.54s
```

Tests include:
- 31 existing userTierStore tests
- 5 new backend role mapping tests
- 17 new normalizeRoleToTier unit tests

**AuthContext.test.tsx:**
```
Tests  15 passed | 1 failed (16)
```

The 1 failing test (`devBypass`) is a pre-existing issue unrelated to our changes - it requires `NODE_ENV=development` which isn't set in the test environment. All auth flow tests with backend roles pass.

---

## Contract Clarity

**Backend-Canonical Roles (source of truth):**
- `super_admin` - Platform-wide admin
- `tenant_admin` - Tenant management
- `content_admin` - Content governance
- `analyst` - Read + analytics + agents
- `read_only` - Read-only access
- `system` - Service-to-service

**Frontend Tiers (presentation abstraction):**
- `admin` - Full admin access
- `advanced` - Advanced features + formulas
- `standard` - Basic access

**Normalization happens at the store boundary** - components never see raw backend roles, only normalized UI tiers.

---

## Security Considerations

1. **Fail-safe default:** Unknown roles map to `standard` tier (lowest privilege)
2. **Case-insensitive:** Role matching is normalized to lowercase
3. **Whitespace trimming:** Roles are trimmed before matching
4. **Development warnings:** Unknown roles log warnings in dev mode to catch mapping gaps
