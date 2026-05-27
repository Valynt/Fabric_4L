# Test Quarantine

**Purpose:** Isolated location for tests that are temporarily failing due to external dependencies, not code defects.

## Quarantined Tests

*No tests currently in quarantine.*

## Running Quarantined Tests

```bash
# Run quarantined tests separately (allowed to fail)
pytest tests/quarantine/ -v --ignore-glob="*README*" || true
```

## Policy

- Tests in quarantine are NOT blocking PRs
- Tests must be fixed and returned to main test suite within 30 days
- Each quarantined test MUST have a tracking issue
- Weekly review of quarantined tests required

## Adding to Quarantine

1. Move test file to `tests/quarantine/`
2. Add skip marker: `pytestmark = pytest.mark.skip(reason="...")`
3. Update this README with test details
4. Create tracking issue
5. Notify team in #qa channel

## Removing from Quarantine

1. Fix the underlying issue
2. Move test back to original location
3. Remove skip marker
4. Update this README
5. Close tracking issue
