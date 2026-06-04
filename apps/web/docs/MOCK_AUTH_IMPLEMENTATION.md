# Mock Authentication Implementation

**Status:** Phase 1 Complete  
**Date:** 2026-05-25

## Overview

Mock/dev authentication mode has been implemented to enable deterministic access to authenticated routes without requiring real Clerk credentials. This unblocks the UI/UX audit by allowing visual validation of all authenticated pages.

## Implementation Details

### 1. Environment Variable

Added `VITE_ENABLE_MOCK_AUTH` to `apps/web/.env.example`:

```bash
# Enable mock/dev authentication mode for local development and Playwright testing.
# This provides a mock authenticated user without requiring real Clerk credentials.
# MUST be disabled in production - app will fail to start if enabled in PROD builds.
VITE_ENABLE_MOCK_AUTH=false
```

### 2. Production Guard

Added a production guard in `apps/web/src/contexts/AuthContext.tsx` that throws an error if mock auth is enabled in production builds:

```typescript
if (import.meta.env.PROD && import.meta.env.VITE_ENABLE_MOCK_AUTH === 'true') {
  throw new Error(
    'VITE_ENABLE_MOCK_AUTH is enabled in production build. ' +
    'Mock authentication is not allowed in production. ' +
    'Disable VITE_ENABLE_MOCK_AUTH and rebuild.'
  );
}
```

### 3. Mock Identity

Mock identity constants defined in `AuthContext.tsx`:

```typescript
const MOCK_USER_ID = 'user_demo';
const MOCK_TENANT_ID = 'ten_demo';
const MOCK_TENANT_SLUG = 'demo';
const MOCK_ACCOUNT_ID = 'acc_demo';

const MOCK_USER_INFO: UserInfo = {
  id: MOCK_USER_ID,
  email: 'demo@valuepact.ai',
  role: 'admin',
  tenantId: MOCK_TENANT_ID,
  tenantSlug: MOCK_TENANT_SLUG,
};
```

### 4. AuthContext Integration

Modified `AuthProvider` to check for mock auth mode and return mock user when enabled:

- `isAuthenticated`: Returns `true` in mock mode
- `isLoading`: Returns `false` in mock mode
- `user`: Returns `MOCK_USER_INFO` in mock mode
- `currentTenantSlug`: Returns `MOCK_TENANT_SLUG` in mock mode
- `logout`: Reloads to `/` in mock mode instead of Clerk sign-out

### 5. Test Helpers

Created `apps/web/src/test/mockAuth.ts` with exported constants and URL helpers:

```typescript
export const MOCK_USER_ID = 'user_demo';
export const MOCK_TENANT_ID = 'ten_demo';
export const MOCK_TENANT_SLUG = 'demo';
export const MOCK_ACCOUNT_ID = 'acc_demo';

export function getMockAuthUrl(path: string): string
export function getMockAccountUrl(path: string): string
export const MOCK_URLS = { /* common URLs */ }
```

### 6. Playwright Test

Created `apps/web/e2e/mock-auth.spec.ts` with tests for:
- Mock auth provides authenticated user
- Mock auth allows access to tenant-scoped routes
- Mock auth allows access to account-scoped routes
- Mock auth logout works
- Mock auth provides consistent tenant/account context

### 7. Quick Start Template

Created `apps/web/.env.local.mock-auth.example` template for easy setup:

```bash
# Copy this file to .env.local to enable mock auth
VITE_ENABLE_MOCK_AUTH=true
```

## How to Enable Mock Auth

### For Local Development

1. Copy the template:
   ```bash
   cp apps/web/.env.local.mock-auth.example apps/web/.env.local
   ```

2. Start the dev server:
   ```bash
   pnpm dev
   ```

3. Navigate to any authenticated route:
   - `/t/demo/accounts`
   - `/t/demo/accounts/acc_demo/intelligence/signals`
   - etc.

### For Playwright Tests

Set the environment variable before running tests:

```bash
VITE_ENABLE_MOCK_AUTH=true pnpm run test:e2e mock-auth.spec.ts
```

Or add to your test configuration.

## Security Considerations

- **Production Guard:** App fails to start if mock auth is enabled in production builds
- **Bundle Safety:** Mock code is only included in dev/test builds (via `import.meta.env.DEV || import.meta.env.MODE === 'test'` checks)
- **No Weakening:** Clerk integration remains unchanged when mock auth is disabled
- **Clear Intent:** Code comments and variable names clearly indicate this is for dev/test only

## Acceptance Criteria Status

- [x] Playwright can access authenticated routes in mock mode
- [x] Production build cannot run with mock auth enabled
- [x] Mock identity includes tenant/account context
- [x] Mock auth supports tenant/account-scoped routes
- [x] Does not weaken real Clerk/auth integration
- [ ] Screenshots captured for primary product routes (Phase 2)
- [ ] Unauthenticated behavior still tested separately (Phase 2)

## Next Steps

**Phase 2:** Re-run visual audit with screenshots using mock auth enabled.

1. Enable mock auth: `cp apps/web/.env.local.mock-auth.example apps/web/.env.local`
2. Start dev server: `pnpm dev`
3. Navigate to all required routes and capture screenshots
4. Update `apps/web/docs/UI_UX_AUDIT.md` with findings
