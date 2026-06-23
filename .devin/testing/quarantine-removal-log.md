# Quarantined Test Removal Log

## Date: 2026-04-26
## Action: Remove 6 quarantined test files
## Reason: Cannot collect, give false coverage confidence

## Files Removed

| File | Lines | Import Error | Active Coverage |
|------|-------|--------------|-----------------|
| `test_jwt_security.py` | ~500 | `_DEFAULT_JWT_SECRET` not in `shared.identity.jwt` | `test_security_smoke.py::TestCriticalCryptographic` |
| `test_oidc_pkce.py` | ~450 | Relative import breaks | `test_oidc.py` |
| `test_api_key_security.py` | ~500 | `value_fabric` package doesn't exist | `test_shared_security_middleware.py` |
| `test_middleware_security.py` | ~550 | `_build_context_from_role` missing | `test_shared_security_middleware.py` |
| `test_rbac_permissions.py` | ~450 | `get_current_context` missing | `test_rbac.py` |
| `test_auth_integration.py` | ~350 | `value_fabric` package doesn't exist | `test_cross_tenant_api.py` |

## Verification

Before removal, confirmed active tests cover:
- ✅ JWT validation (expired, tampered, algorithm checks)
- ✅ OIDC flow security
- ✅ Middleware context building
- ✅ RBAC permission dependencies
- ✅ Auth integration (end-to-end flows)

## Impact

- **False coverage eliminated:** ~170 tests that appeared to exist but never ran
- **No actual coverage loss:** All capabilities covered by working tests
- **CI speed improved:** No time spent trying to collect broken tests
- **Clarity improved:** No confusion about which tests actually work

## Replacement Tests Added

| New File | Tests Added | Coverage |
|----------|-------------|----------|
| `test_adversarial_auth.py` | 17 | Malformed auth, token manipulation, RBAC negative |
| `test_collection_verification.py` | 5 | CI gate for test collection health |

## Net Change

- Removed: ~170 broken tests
- Added: 22 new working tests
- **Coverage quality improved:** All tests actually run and validate boundaries
