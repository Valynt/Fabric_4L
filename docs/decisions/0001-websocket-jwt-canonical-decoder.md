# ADR-0001: WebSocket JWT Canonical Decoder

- **Status**: accepted
- **Date**: 2024-01-15
- **Deciders**: Security Hardening Team
- **Stakeholders**: Layer 4 Agents Team, Security Audit, WebSocket Consumers

## Context

The Layer 4 WebSocket authentication path was calling `decode_jwt()` with two positional arguments (`token` and `JWT_SECRET`), but the canonical `decode_jwt()` signature only accepts `token` and reads `JWT_SECRET` internally from the application configuration.

This mismatch produced the runtime error:

```
Authentication failed: Token validation failed: TypeError;
decode_jwt() takes 1 positional argument but 2 were given
```

This is a contract mismatch between the WebSocket route code and the shared authentication library. The Layer 4 route was authored against an older or assumed signature of `decode_jwt()`. All other auth paths (REST middleware, service-to-service) already use the single-argument form.

## Decision

Change the Layer 4 WebSocket auth handler to call `decode_jwt(token)` without passing `JWT_SECRET` as a second positional argument. The canonical decoder reads the secret from config internally.

### File changed

- `services/layer4-agents/src/layer4_agents/api/websocket/routes.py`
  - Before: `decode_jwt(token, JWT_SECRET)`
  - After: `decode_jwt(token)`

### Test changes

- `tests/security/test_p1_13_websocket_auth.py`
  - Patched the decoder with valid claims for success-path tests
  - Changed the `None` token assertion to expect `WebSocketAuthError` instead of a bare `None` return

### Behavior preserved

- Missing or invalid tokens still trigger fail-closed behavior: the WebSocket connection is closed with code `1008` (Policy Violation)
- No fallback to unauthenticated access

## Consequences

### Positive
- WebSocket auth aligns with the canonical `decode_jwt()` contract used everywhere else
- Eliminates the `TypeError` on every WebSocket connection attempt
- Security test suite passes with 3/3 tests green
- Fail-closed behavior is preserved and explicitly tested

### Negative / Risks
- Any code still expecting the two-argument form will break silently at call sites (no compile-time check in Python)
- Assumes `JWT_SECRET` is always present in config; missing config will now surface as a config error inside `decode_jwt()` rather than a caller-side `TypeError`

### Neutral
- Token validation logic itself does not change -- only the call-site contract
- `JWT_SECRET` value is unchanged; only who supplies it changes

## Validation

Run the WebSocket auth security test:

```bash
python -m pytest tests/security/test_p1_13_websocket_auth.py -n 0 --maxfail=1 -vv
```

**Expected output:**
```
tests/security/test_p1_13_websocket_auth.py::test_websocket_auth_valid_token PASSED
tests/security/test_p1_13_websocket_auth.py::test_websocket_auth_invalid_token PASSED
tests/security/test_p1_13_websocket_auth.py::test_websocket_auth_missing_token PASSED

3 passed
```

## Related
- Related ADRs: [ADR-0004: Layer 4 Database Facade Compatibility](0004-layer4-database-facade-compatibility.md) -- both fix Layer 4 contract/export issues
- Related files:
  - `services/layer4-agents/src/layer4_agents/api/websocket/routes.py`
  - `tests/security/test_p1_13_websocket_auth.py`
- Related tests:
  - `python -m pytest tests/security/test_p1_13_websocket_auth.py -n 0 --maxfail=1 -vv`
