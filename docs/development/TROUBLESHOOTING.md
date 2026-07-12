# Developer Troubleshooting Guide

Quick reference for the canonical verification gates and the most common local/CI failures encountered while working on the Value Fabric monorepo.

For the full build/test command reference see [`BUILD_SYSTEM.md`](BUILD_SYSTEM.md) and [`COMMANDS.md`](COMMANDS.md). For routing issues to source-of-truth files see [`DISCOVERY_MAP.md`](DISCOVERY_MAP.md).

## Canonical one-command verification

Run these gates in order before opening a PR. The final gate (`make verify`) must pass.

```bash
# 1. Lint every layer
make lint

# 2. Type-check every layer
make typecheck

# 3. Contract and architecture tests
make contract-tests

# 4. Frontend unit tests
pnpm --dir apps/web run test

# 5. Final verification gate (runs all of the above plus structural/security checks)
make verify
```

## Common failures and fixes

### `check-behavior-contract`: allowed/denied test not found

**Symptom:**

```text
Behavior Contract Gate
1 violation(s):
  - [governance.governance-middleware] allowed test 'test_public_path_bypasses_auth' not found in tests/security/test_governance_middleware_resolution_order.py
make: *** [Makefile:236: check-behavior-contract] Error 1
```

**Cause:** The behavior contract in `contracts/behavior-contract.yaml` maps capabilities to specific test names. Renaming or deleting a test without updating the contract breaks the gate.

**Fix:**

1. Find the capability in `contracts/behavior-contract.yaml`.
2. Update `allowed.test` or `denied.test` to the new test name.
3. Re-run `make check-behavior-contract` before `make verify`.

```bash
make check-behavior-contract
```

**Prevention:** Include the behavior-contract gate in local verification before pushing. Avoid renaming security-behavior tests unless the contract is updated in the same commit.

---

### Redaction regex matches UUIDs or other non-sensitive tokens

**Symptom:** Tests that pass UUID-like strings through `redact_credentials()` or `detect_pii()` fail because the regex matches 32-character hex strings, GUIDs, or object IDs.

**Example:** A credit-card pattern of `\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b` matches `00000000-0000-0000-0000-000000000001`.

**Fix:** Anchor patterns to the exact shape of the sensitive data. For 16-digit credit cards with dashes, prefer:

```python
_CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")
```

For PII detection, keep the broader pattern only where the surrounding context (e.g., field name, provider) disambiguates it from UUIDs.

**Related files:**

- `packages/shared/src/value_fabric/shared/security/redaction.py`
- `services/api/app/services/pii_detection_service.py`
- `packages/shared/src/value_fabric/shared/security/tests/test_redaction.py`
- `services/api/app/tests/test_pii_redaction.py`

---

### `python_contract_lint` `security_todo` false positives

**Symptom:** `make lint` fails with `python_contract_lint` reporting `security_todo` markers in test files even though no actual TODO is present.

**Cause:** The linter flags strings such as `bypasses_auth`, `todo_auth`, or similar substrings inside test names, docstrings, or assertion messages.

**Fix:** Rename the offending identifier to a synonym that does not contain the flagged substring, then update the behavior contract if the test is registered there.

**Example:** Rename `test_public_path_bypasses_auth` to `test_public_path_skips_authentication` and update `contracts/behavior-contract.yaml` accordingly.

---

### JWT secret pollution across tests

**Symptom:** Security tests pass in isolation but fail when run together, or API tests fail with `Invalid token` after upstream security test modules run.

**Cause:** A shared JWT secret environment variable (e.g., `JWT_SECRET`) is set conditionally with `setdefault`, allowing earlier tests to pin a different secret that is then used by later test modules and the app under test.

**Fix:** Force the test secret with direct assignment in the API test conftest:

```python
# services/api/app/tests/conftest.py
_os.environ["JWT_SECRET"] = TEST_SECRET
```

Do **not** use `setdefault` for secrets that the app and tests must agree on.

---

### DSAR idempotency returns duplicate requests

**Symptom:** Replaying a `POST /v1/privacy/dsar` request with the same `Idempotency-Key` creates a second DSAR instead of returning the first response.

**Cause:** The endpoint swallowed `IdempotencyConflictError` or did not return the cached response on replay.

**Fix:** Ensure the route:

1. Builds a stable request fingerprint.
2. Calls `service.check_replay(...)` and returns `replay.body` when a cached response exists.
3. Raises `HTTPException(status_code=409)` when `IdempotencyConflictError` is raised (different payload, same key).

**Related files:**

- `services/api/app/routers/privacy.py`
- `services/api/app/tests/test_privacy_dsar.py`

---

### JWT debug prints leak headers/payloads

**Symptom:** Log output or test captures contain raw JWT headers, payloads, or signing keys.

**Cause:** `print()` statements left in JWT decoding/encoding code for local debugging.

**Fix:** Remove all `print()` calls from JWT paths and add a regression test that asserts no stdout/stderr is emitted during decode and that no `print()` calls remain in the module.

**Related files:**

- `packages/shared/src/value_fabric/shared/identity/jwt.py`
- `packages/shared/src/value_fabric/shared/identity/tests/test_jwt.py`

---

## Per-layer focused test commands

Use these for faster feedback while developing.

```bash
# Single Python service
python -m pytest services/api/app/tests/test_privacy_dsar.py -v

# Single layer
make test-layer4

# Contract tests only
make contract-tests

# Frontend tests only
pnpm --dir apps/web run test
```

## Still stuck?

1. Check [`DISCOVERY_MAP.md`](DISCOVERY_MAP.md) for the source-of-truth file and validation command for the area you changed.
2. Run the narrowest failing gate directly (e.g., `make check-behavior-contract`) instead of the full `make verify` loop.
3. For security-sensitive changes, run the security smoke tests:
   ```bash
   python -m pytest tests/security/test_security_smoke.py -v
   ```
