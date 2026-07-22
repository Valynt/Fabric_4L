## Summary

Hardens the L4 invitation acceptance flow with atomic token consumption, uniform error responses, per-IP rate limiting, and a frontend redemption page.

## Changes

### L4 Backend
- **invitations.py**: `verify_token` now uses Redis `GETDEL` for atomic token consumption, preventing TOCTOU race conditions where two concurrent requests could both read the same valid token. `mark_token_used` is deprecated as a no-op.
- **service.py**: `accept_invitation` raises uniform `HTTPException(401, "Invalid or expired invitation token")` for all failure modes (invalid/expired/consumed token, user not found, already accepted) to prevent information leakage.
- **users.py**: Added `IPRateLimitDependency(10/min)` to the public `POST /accept-invite` endpoint for brute-force protection.

### L4 Tests
- Updated all failure-mode tests to assert `HTTPException` with 401 status code.
- Removed `mark_token_used` assertion from success test (token is now consumed atomically in `verify_token`).

### Frontend
- **useGovernance.ts**: Added `useAcceptInvite` mutation hook calling L4 `POST /users/accept-invite`.
- **AcceptInvite.tsx**: New invitation redemption page with token, display name, password + confirm fields, and error handling.
- **AcceptInvite.test.tsx**: 3 tests covering success redirect, password mismatch, and backend rejection.
- **router.tsx**: Registered public `/accept-invite` route.

## Governance Impact
- **Contract shape**: No API contract changes — L4 `POST /users/accept-invite` request/response shape unchanged.
- **Tenant isolation**: Uniform 401 prevents cross-tenant information leakage from error response differentiation.
- **Security**: Atomic GETDEL eliminates token replay race; rate limiting mitigates brute-force token guessing.

## Validation
- `pytest tests/test_tenant_invitations.py` — 16 passed
- `vitest run src/pages/AcceptInvite.test.tsx` — 3 passed
- `pytest app/tests/test_invitation_and_tenant_leakage.py app/tests/test_tenant_isolation.py` — 19 passed (no regression)

Co-authored-by: Ona <no-reply@ona.com>
