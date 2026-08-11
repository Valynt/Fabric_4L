# Packet (d) — Risk Waiver Drafts (for owner signature; agent grants nothing)

- **UTC:** 2026-08-11T05:00:00Z
- **Source:** `production-readiness/risk_register.yaml` @ main `e3ace52032f8c80436e46adee4fba27402ae9f31` (risks quoted verbatim below)
- **Rule (launch contract):** environment-dependent risks may be waived only by the named risk owner, with a signed waiver entry and an expiry date. These are DRAFTS; the named owner signs or rejects. No agent may grant or extend a waiver.
- **Proposed expiry for all drafts:** 2026-08-25 (14 days). Rationale: long enough to provision staging (packet h) and run the evidence, short enough to force re-litigation rather than silent expiry.
- **Schema:** draft entries conform to `release/v1/schemas/risk-register.schema.json` (`waiver`: `approved_by`, `reference`, `expires`; `additionalProperties: false`). Scope and unblock prose lives in the markdown around each entry, not inside the YAML object.

| Risk | Severity | Owner (register) | Environment-dependent? | Draft waiver? |
|---|---|---|---|---|
| PRR-002 Tenancy evidence | P0 | Platform Security | Partially — full aggregate gate needs Redis-configured env | Yes (narrowed after #1269/#1271) |
| PRR-003 Golden path | P0 | Platform Engineering | Yes — staging | Yes |
| PRR-006 Observability | P1 | SRE | Yes — staging receivers | Yes |
| PRR-007 Billing | P1 | Product Engineering | Yes — live provider sandbox OR out-of-scope decision | Superseded by packet (a) decision — sign ONE of them |
| PRR-008 Compliance evidence | P1 | Compliance Owner | No — owner review is the unblock | Yes (signature itself is the exit) |
| PRR-010 Env-dependent P0 certification | P0 | Release Management + respective owners | Yes — staging | Yes |

## Draft waiver entries (paste-ready, schema-conformant)

### PRR-002 — Tenancy evidence (narrowed scope)

Scope: full aggregate tenant-isolation gate requiring a Redis-configured environment. NOT waived: hostile static tests (49/49), route tenant propagation evidence, and the queue-plane hardening landed in #1269/#1271 (`test_worker_kill_switch_and_idempotency.py` 8/8, `test_l2_extraction_tenant_binding.py` 4/4). Unblock: `signoff-evidence/gates/staging-environment-request.md` → run the full aggregate gate in staging.

```yaml
- id: PRR-002
  waiver:
    approved_by: "<Platform Security — signature required>"
    reference: "signoff-evidence/gates/risk-waivers.md#prr-002"
    expires: "2026-08-25"
```

### PRR-003 — Golden path

Scope: P0 Playwright journey evidence and golden-path certification requiring configured staging (V1-GOLDEN-001/002). NOT waived: `make verify`, local critical-path smoke, `make production-readiness-gate`. Unblock: packet (h) → `make certify-meridian-journey` + `make test-backend-integrated-release-smoke` + `test:e2e:live`.

```yaml
- id: PRR-003
  waiver:
    approved_by: "<Platform Engineering — signature required>"
    reference: "signoff-evidence/gates/risk-waivers.md#prr-003"
    expires: "2026-08-25"
```

### PRR-006 — Observability

Scope: receiver/dashboard/log-trace evidence for journeys j01–j05 requiring staging. NOT waived: `pnpm test:observability`, `pnpm lint:logs`, metrics endpoint reachability. Unblock: packet (h) → `pytest tests/observability tests/reliability tests/recovery` + receiver delivery evidence.

```yaml
- id: PRR-006
  waiver:
    approved_by: "<SRE — signature required>"
    reference: "signoff-evidence/gates/risk-waivers.md#prr-006"
    expires: "2026-08-25"
```

### PRR-007 — Billing (decision-linked)

Do NOT sign a waiver here if packet (a) resolves `paid_billing_in_scope`. If the decision is "out of scope", record the decision instead — no waiver needed. If the decision is "in scope", no waiver is valid: paid GA requires live provider sandbox evidence.

```yaml
- id: PRR-007
  waiver:
    approved_by: "<Product Engineering — decision per packet (a), not a waiver>"
    reference: "signoff-evidence/gates/paid-billing-scope.md"
    expires: "2026-08-25"
```

### PRR-008 — Compliance evidence

Scope: auditable owner review of control evidence. The signature itself is the exit criterion; expiry forces re-review if the evidence set changes. Unblock: owner review of `signoff-evidence/` + `compliance/evidence/`.

```yaml
- id: PRR-008
  waiver:
    approved_by: "<Compliance Owner — signature required>"
    reference: "signoff-evidence/gates/risk-waivers.md#prr-008"
    expires: "2026-08-25"
```

### PRR-010 — Environment-dependent P0 certification

Scope: P0-001 Playwright journeys and P0-002 rollback rehearsal requiring a configured launch environment. P0-003 SSO stays scoped out of Core GA per `docs/launch/sso-core-ga-scope-decision.md` (already recorded). Unblock: packet (h) → P0-001/002 certification in staging.

```yaml
- id: PRR-010
  waiver:
    approved_by: "<Release Management + respective owners — signatures required>"
    reference: "signoff-evidence/gates/risk-waivers.md#prr-010"
    expires: "2026-08-25"
```

## Approval blocks (one per entry; unsigned entries are NOT waived)

```
PRR-___ waiver signed. Expiry 2026-08-25 acknowledged.
Name: ______________  Role: ______________  Date (UTC): __________
```
