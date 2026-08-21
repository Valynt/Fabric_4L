# Secret Fixture Standard

> Defines allowed formats for synthetic test fixtures that resemble real
> secret patterns, and the scanner allowlist process for registering them.
>
> Companion to: ADR-038, `docs/security/secrets-management.md`,
> `docs/runbooks/security/respond-to-secret-leak.md`

---

## Purpose

Automated secret scanners (gitleaks, GitHub push protection) detect patterns
matching real credential formats. Synthetic test fixtures that exercise
redaction, validation, or authentication logic may trigger these scanners.
This standard defines how to create fixtures that are clearly synthetic while
remaining useful for testing, and how to register them in scanner allowlists.

---

## Allowed Fixture Formats

### Stripe

| Type | Format | Example |
|---|---|---|
| Test publishable key | `pk_test_` + dummy chars | `pk_test_dummy_1234567890abcdef` |
| Test secret key | `sk_test_` + dummy chars | `sk_test_dummy_1234567890abcdef` |
| Prohibited | `sk_live_`, `pk_live_` | Never use live key prefixes in fixtures |

### JWT

| Type | Format | Example |
|---|---|---|
| Test token | `eyJ` + base64 of `{"test": true}` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_test_payload.dummy_test_signature` |
| Prohibited | Real signed tokens with valid secrets | Never use tokens signed with production secrets |

### API Keys (generic)

| Type | Format | Example |
|---|---|---|
| Test key | `test_` + descriptive suffix | `test_api_key_for_redaction_unit_test` |
| Prohibited | Real provider key formats without `test_` prefix | `fab_`, `sk_`, `xoxb-` (unless prefixed with `test_`) |

### Database URLs

| Type | Format | Example |
|---|---|---|
| Test URL | Non-routable host + dummy creds | `postgresql://test_user:test_pass@localhost:5432/test_db` |
| Prohibited | Real connection strings with production hosts | Any URL with a real hostname and credentials |

---

## Scanner Allowlist

### Allowlist File

Location: `.gitleaks-allowlist.toml` (or equivalent scanner-specific format)

Each entry must include:

```toml
[[allowlist]]
path = "tests/security/test_secret_redaction_responses.py"
description = "Test fixture for secret redaction logic"
owner = "security-team"
expires = "2026-12-31"
reason = "Synthetic Stripe test key (sk_test_dummy_*) used to verify redaction coverage"
```

### Required Fields

| Field | Description |
|---|---|
| `path` | File path containing the fixture (glob patterns allowed) |
| `description` | Human-readable description of the fixture |
| `owner` | Team or individual responsible for the fixture |
| `expires` | Expiry date (YYYY-MM-DD); entry must be renewed or removed |
| `reason` | Justification for why the fixture is synthetic and safe |

### Allowlist Review

- Monthly review of all entries
- Expired entries are removed; fixtures must be re-justified
- Owner is notified 30 days before expiry
- No permanent allowlist entries — all must have an expiry

---

## Prohibited Fixture Patterns

- Real key formats without sandbox designation (e.g., `sk_live_...` in any file)
- Tokens signed with production secrets
- Database URLs with real hostnames and credentials
- API keys obtained from real providers, even if revoked
- Secrets copied from production "for testing"

---

## Test Assertions

Tests using synthetic fixtures should include assertions proving the fixture
cannot authenticate:

```python
def test_fixture_cannot_authenticate():
    """Verify that test fixtures are non-functional against real services."""
    fixture_key = "sk_test_dummy_1234567890abcdef"
    # Assert the fixture is rejected by any real API
    # (mock the API call, verify it would be rejected)
    assert fixture_key.startswith("sk_test_")
    assert "dummy" in fixture_key
```

---

## Related Documents

- `docs/security/secrets-management.md` — Infisical architecture
- `docs/runbooks/security/respond-to-secret-leak.md` — Incident response
- `docs/governance/manifest-secret-injection-policy.md` — K8s manifest policy
- ADR-038: Externalized Secret Management and Automated Secret Detection
- `.pre-commit-config.yaml` — gitleaks hook configuration

---

*Last updated: 2026-07-20*
