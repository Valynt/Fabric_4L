# Behavior Contract Template

Use this template when defining a new behavioral contract for a production-critical workflow.

---

## Domain

<!-- e.g., Auth, Tenant Isolation, API Access, Configuration, Data Boundaries -->

## Capability

<!-- One-sentence description of the capability under test -->

## Intended Allowed Behavior

<!-- What should happen when a valid actor performs a valid action -->

### Test

```python
# File: tests/{contract,security,integration}/test_<domain>_<capability>.py

@pytest.mark.<marker>
def test_<allowed_behavior_description>():
    """<Actor> with <valid context> can <perform valid action>."""
    # Arrange
    ...
    # Act
    ...
    # Assert
    assert result.status_code == 200
    assert result.data == expected
```

## Intended Denied Behavior

<!-- What should happen when an invalid actor, invalid action, or out-of-scope request occurs -->

### Test

```python
# File: tests/{contract,security,integration}/test_<domain>_<capability>.py

@pytest.mark.<marker>
def test_<denied_behavior_description>():
    """<Actor> without <required context> is denied and fails closed."""
    # Arrange
    ...
    # Act
    ...
    # Assert
    assert result.status_code == 401  # or 403, 400, etc.
    assert result.error_code == "EXPECTED_ERROR_CODE"
    assert no_side_effect_occurred
```

## Expected Failure Mode

<!-- Explicit error codes, HTTP status codes, exceptions, or safe defaults -->

| Scenario | Status Code | Error Code | Safe Default |
|----------|-------------|------------|--------------|
| Missing auth | 401 | `AUTH_REQUIRED` | Empty response |
| Invalid tenant | 403 | `TENANT_FORBIDDEN` | Empty response |
| Invalid payload | 422 | `VALIDATION_ERROR` | Rejected write |
| ... | ... | ... | ... |

## Test or Gate Enforcing the Behavior

<!-- pytest marker, CI job, Makefile target, or pre-commit gate -->

- **Marker:** `@pytest.mark.<marker>`
- **CI Job:** `<job_name>` in `.github/workflows/pr-checks.yml`
- **Makefile target:** `make <target>`
- **Command:** `pytest <path> -m <marker> -v`

## Cross-Layer Impact

<!-- If this behavior spans layers, list the cross-layer contract test file -->

- `tests/contract/test_layer_integration.py`
- `tests/contract/test_<layer>_frontend_contract.py`

## Checklist

- [ ] The intended allowed behavior has a passing test.
- [ ] The intended denied behavior has a passing test.
- [ ] The failure mode is explicit and tested.
- [ ] A CI gate or marker exists to enforce the behavior on every PR.
- [ ] If the behavior spans layers, a cross-layer contract test exists.
- [ ] If the behavior is security-sensitive, a hostile test exists.

---

## Examples by Domain

### Auth Behavior

```python
# Allowed
@pytest.mark.security
def test_authenticated_user_with_valid_token_can_access_protected_resource():
    ...

# Denied
@pytest.mark.security
def test_unauthenticated_request_to_protected_resource_fails_closed_with_401():
    ...
```

### Tenant Isolation

```python
# Allowed
@pytest.mark.tenant_boundary
def test_tenant_admin_can_read_own_tenant_data():
    ...

# Denied
@pytest.mark.tenant_boundary
def test_tenant_a_cannot_read_tenant_b_data():
    ...
```

### Configuration Validity

```python
# Allowed
@pytest.mark.contract_static
def test_valid_configuration_passes_startup_validation():
    ...

# Denied
@pytest.mark.contract_static
def test_invalid_configuration_fails_startup_with_explicit_error():
    ...
```

### Environment Safety

```python
# Denied (there is no allowed path for dev bypass in production)
@pytest.mark.contract_static
def test_dev_auth_bypass_in_production_mode_fails_startup():
    ...
```

### Frontend User Flows

```typescript
// Allowed
it("allows authenticated user to submit value pack", async () => {
  ...
});

// Denied
it("disables submit when required fields are missing", async () => {
  ...
});
```
