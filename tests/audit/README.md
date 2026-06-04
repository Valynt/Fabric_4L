# Audit Readiness Suite

## What This Suite Validates

This suite centralizes audit readiness for admin actions, support impersonation, auth events, permission changes, billing changes, and audit log tamper resistance.

## Production Risks Covered

- Privileged actions without structured audit events.
- Support impersonation without tenant scope, reason, or approval metadata.
- Auth failures or sensitive route access missing correlation and audit context.
- Audit records that can be mutated or restored without chain/integrity evidence.

## Existing Coverage Aggregated

- `tests/shared/audit/test_ledger_chain.py`
- `tests/security/test_privileged_audit.py`
- `tests/security/test_auth_logging.py`
- `tests/security/test_sensitive_route_audit_coverage.py`
- `tests/integration/test_admin_audit_journey.py`
- `services/layer5-ground-truth/tests/test_audit_append_only_guards.py`
- `.github/workflows/audit-evidence.yml`

## Known Gaps

- BILLING_AUDIT_EVENT_FIXTURE: billing state is covered by recovery and entitlement tests, but a dedicated local billing audit event fixture is still needed.
- SUPPORT_PROVIDER_SESSION_REPLAY: support impersonation is unit/integration tested, not replayed against a live identity provider.

## How To Run

```bash
pytest tests/audit/
pnpm test:audit
```

## CI Artifact

CI should publish `artifacts/production-readiness/audit/junit.xml` and `artifacts/production-readiness/audit/summary.md`.

