# Decision Packet — Gate: `paid_billing_in_scope` (v1.0.0)

- **Repo:** bmsull560/Fabric_4L, main = `e3ace52032f8c80436e46adee4fba27402ae9f31` (merge of PR #1271, HEAD at drafting)
- **Gate:** `paid_billing_in_scope` — is paid billing in scope for v1.0.0?
- **Authority:** Product + Release Management (per `release/v1/launch-contract.yaml:59-62`)
- **Status of this document:** recommendation + evidence only. This packet does NOT record the decision; the named authority does.

---

## 1. Decision requested (exact text for the human authority)

The authority records ONE of the two options by pasting this entry into
`production-readiness/risk_register.yaml` under PRR-007 and flipping
`release/v1/launch-contract.yaml` `scope_decisions.paid_billing_in_scope.decision`
from `pending` to the chosen value:

```yaml
    scope_decision:
      gate: paid_billing_in_scope
      decision: <out-of-scope-for-v1.0.0 | in-scope-for-v1.0.0>
      authority: Product + Release Management
      decided_by: <name>
      date: <YYYY-MM-DD>
      rationale: >
        <one sentence; if in-scope, must cite live provider sandbox evidence
        satisfying the PRR-007 exit criteria>
      evidence: signoff-evidence/gates/paid-billing-scope.md
```

Until this entry exists, the gate remains a launch blocker (`launch-contract.yaml:51-53`:
"pending entries are launch blockers until a named human authority records a decision here").

## 2. Recommendation

**Paid billing: OUT of scope for v1.0.0.** Keep plan/trial/entitlement enforcement
(journey j05) in scope; ship no paid checkout, no customer portal, no metered overage
billing in v1.0.0. Justification:

- PRR-007's own exit criteria (`production-readiness/risk_register.yaml:112-114`) require
  "live provider sandbox or explicit out-of-scope decision" for paid launch. No live or
  sandbox Stripe evidence exists anywhere in the repo — the three provider-dependent
  behaviors (checkout redirect, dunning payload replay, provider-clock period-end) are
  explicitly documented as unexercised gaps in `tests/billing/README.md:39-43`
  (`CHECKOUT_PROVIDER_SANDBOX`, `PAYMENT_FAILURE_PROVIDER_EVENT`,
  `CANCELLATION_GRACE_PERIOD_PROVIDER_CLOCK`).
- The canonical billing service `services/layer7-billing/` has no Kubernetes Deployment
  manifest — only its Postgres database is provisioned (`k8s/base/postgres.yml`,
  `k8s/envs/production-data/kustomization.yaml` DATABASES list). Paid billing would ship
  on a service with no production deploy path; it appears only in
  `infra/compose/docker-compose.full.yml:512`.
- PRR-007's status_note already anticipates this outcome: "Scope out if unpaid"
  (`risk_register.yaml:107`). An unpaid v1.0.0 makes out-of-scope the internally
  consistent decision.

## 3. Evidence (all SHAs on main `e3ace52032f8`)

**PRR-007 entry, quoted verbatim** (`production-readiness/risk_register.yaml:102-114`,
file last modified in `4b5b79bc0ada46b480f56cca42c81f15ff635e7f`):

> id: PRR-007 / area: Billing / severity: P1 / owner: Product Engineering /
> status: ACCEPTED / status_note: "Scope out if unpaid; pending owner countersignature
> for paid GA." / risk: "Paid launch without metering, entitlement, idempotency, and
> reconciliation evidence risks revenue and customer trust." / validation: "make
> production-readiness-gate billing tests pass" / exit_criteria: "Billing regression
> evidence present locally; paid launch requires live provider sandbox or explicit
> out-of-scope decision."

**Launch contract** (`release/v1/launch-contract.yaml:59-62`, file last modified in
`c2dcb1e528f44ca07d49c7ba81f067fdebf1c6d7`): `paid_billing_in_scope: decision: pending`,
authority Product + Release Management, reference PRR-007.

**Implementation maturity — what exists:**

- Canonical service: `services/layer7-billing/src/layer7_billing/` (last commit
  `4a271708071b59b8e179b98ce099764e98ee06e6`). Per
  `docs/reference/layer-runtime-path-governance.md:44`, this is the deployable billing
  path; `services/billing/` is "non-deployable legacy compatibility only".
- Routes: subscription, checkout, portal, invoices, usage, overages
  (`api/routes/billing.py`, `billing_usage.py`, `billing_overages.py`,
  `billing_webhooks.py`). Tenant-scoped: every handler derives `tenant_id` from
  authenticated context (`ctx.tenant_id`), e.g. `api/routes/billing.py:143,168,188,212,231,249,320`.
- Stripe webhook signature verification: `webhook_security.py:51`
  (`verify_stripe_webhook_signature`).
- L4 facade route: `services/layer4-agents/src/layer4_agents/api/routes/billing.py`
  (1423 lines), tenant-scoped via `context.tenant_id` (e.g. lines 92, 527, 606, 641);
  checkout uses provider-managed subscription sessions
  (`services/layer4-agents/src/layer4_agents/services/billing_service.py`, asserted by
  `tests/billing/test_checkout_flow.py`).

**What is tested (62 test functions in layer7 alone):**

- `services/layer7-billing/tests/`: `test_stripe_webhook_security.py` (5),
  `test_webhook_idempotency_integration.py` (6), `test_cross_tenant_hostile.py` (6),
  `test_tenant_isolation.py` (20), `test_auth_enforcement.py` (10),
  `test_l7_billing_auth_required.py` (8), `test_api_tenant_propagation.py` (7).
  Note: `conftest.py` uses mocked auth (`auth_source="mock"`, line 99) and a mocked DB
  session (lines 164-171) — these are unit-level, not live-stack.
- `tests/billing/` (9 files): production-readiness manifest tests asserting paths,
  documented gaps, and implementation shape — not behavioral runs against a provider.
- `tests/tenancy/test_billing_tenant_scope.py` exists (j05 cites it).
- CI: job `Billing/Entitlements Regression + Evidence`
  (`.github/workflows/pr-checks.yml:2258-2303`) runs
  `pytest tests/integration/billing_entitlements/` and uploads JUnit + summary
  artifacts. The pack's own docstring states it is "intentionally
  implementation-agnostic" — it validates local behavioral-contract dataclasses, not
  the deployed service.
- `Makefile:766`: `billing` is in `PRODUCTION_READINESS_SUITES` (PRR-007 validation hook).

**What is missing:**

- No live/sandbox Stripe evidence: no sandbox replay artifacts; documented gaps in
  `tests/billing/README.md:39-43`; `STRIPE_WEBHOOK_SECRET` empty in `.env.example:353`.
- No k8s production Deployment for layer7-billing (database only; see §2).
- j05 gap, self-declared (`release/v1/journeys/j05-billing-entitlements.yaml`, evidence.gaps):
  "Billing participation in the executable golden-path certification where promised in
  v1 (task V1-GOLDEN-001)" — billing is not in the golden-path certification.

## 4. Blast radius of both options

**If paid billing is declared IN scope for v1.0.0:**

- PRR-007 exit criteria are unmet on current evidence (no provider sandbox) → the P1
  risk "risks revenue and customer trust" ships open; the gate would need either new
  sandbox evidence or a signed waiver before launch.
- Paid flows ship blind on exactly the three provider-dependent behaviors the repo
  documents as unexercised (checkout redirect, dunning, provider-clock cancellation).
- The service has no production k8s deployment — in-scope implies new deploy, secrets
  (`STRIPE_WEBHOOK_SECRET` et al.), and monitoring work not currently evidenced.
- j01–j04: unaffected (no billing references in those journey files — verified by grep).
  j05 stays P0 and must additionally cover paid states.
- The `Billing/Entitlements Regression + Evidence` CI job keeps passing either way —
  it is implementation-agnostic, so a green job is NOT evidence of paid-launch readiness.

**If paid billing is declared OUT of scope for v1.0.0:**

- j05 narrows to plan/trial/entitlement/webhook-integrity outcomes (its
  `allowed_behavior`/`denied_behavior` already read this way); the checkout/portal/overage
  surface must be hidden and server-disabled per `launch-contract.yaml:58`
  (`incomplete_features_policy: hidden and server-disabled, never client-hidden only`).
- j01–j04: unaffected. Contracts: `contracts/openapi/layer7-billing.json` stays valid;
  no response-shape change is required by scoping out.
- The CI job continues to run unchanged and continues to emit the launch-checklist
  evidence artifact; its green status then correctly covers the entitlement-only scope.
- PRR-007 closes via the "explicit out-of-scope decision" branch of its exit criteria;
  paid GA re-enters through a post-v1 scope decision with sandbox evidence.

## 5. Approval (one signature)

Decision (circle one):  PAID BILLING IN SCOPE  /  PAID BILLING OUT OF SCOPE  for v1.0.0

- Name:  ______________________________
- Role:  Product + Release Management authority
- Date:  ______________________________
- Signature:  ______________________________
