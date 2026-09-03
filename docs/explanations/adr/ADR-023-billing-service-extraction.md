# ADR-023: Billing Service Extraction

**Status:** Superseded — Layer 4 ratified as canonical single billing owner (2026-09-01); `services/layer7-billing/` deleted (Brooks-Lint R3 Knowledge Duplication resolution); `services/billing/` removed 2026-08-27 (COMPAT-BILL-001)
**Date:** May 29, 2026
**Authors:** Architecture Lead, Backend Lead
**Reviewers:** Platform Architecture Committee

---

## Context

The Stripe billing logic in `services/layer4-agents/` (`services/billing_service.py`, `api/routes/billing.py`) is co-located with the LangGraph agentic workflow engine. These two concerns have fundamentally different:

- **Change velocity:** Billing changes quarterly (compliance, Stripe API versions); workflow engine changes daily.
- **Scaling profile:** Billing is CPU-light HTTP + DB; LangGraph is CPU/memory-heavy with state checkpoints.
- **External API boundary:** Stripe is a well-defined external boundary; moving it to a dedicated service reduces blast radius.
- **Team ownership:** Billing is owned by the Platform team; workflow engine by the Agents team.

Historically, a separate `services/layer7-billing/` service was created as a phase-1 stub for usage-event tracking and plan entitlements, while complete Stripe-integrated subscription management, checkout sessions, customer portal, customer sync, webhooks, overage calculations, usage events, and invoice charging lived inside `services/layer4-agents/`.

This ADR records the historical extraction proposal, its subsequent supersession, and the final 2026-09-01 consolidation:
1. **2026-05-29:** Initial proposal to extract `services/billing/` from L4.
2. **2026-06-05 / 2026-08-27:** `services/billing/` legacy compatibility package deleted (COMPAT-BILL-001) due to zero production consumers.
3. **2026-09-01 (Final):** Brooks-Lint R3 finding ("Knowledge Duplication — Billing domain logic implemented twice across L4 and L7") resolved by ratifying `services/layer4-agents/` as the single canonical billing owner and deleting `services/layer7-billing/`. Investigation confirmed `layer7-billing` was an incomplete Phase-1 stub with zero production callers and no database migrations, while `services/layer4-agents/` contained the full, tested, production-consumed Stripe billing engine. The billing OpenAPI contract (`contracts/openapi/layer7-billing.json`) is retained and exported directly from the Layer 4 billing application.

## Decision

The original decision was to create **`services/billing/`** (and subsequently `services/layer7-billing/`) as a standalone FastAPI service.

**Final ratified decision (2026-09-01):**
1. **Single Owner:** `services/layer4-agents/` (`services/layer4-agents/src/layer4_agents/api/routes/billing*.py`, `services/billing_service.py`, `models/billing.py`) is the sole canonical billing runtime and persistence owner.
2. **Layer 7 Decommissioned:** `services/layer7-billing/` is completely deleted from the repository, including its Docker, Compose, and Kubernetes definitions.
3. **OpenAPI Contract Retained:** `contracts/openapi/layer7-billing.json` is retained as the authoritative OpenAPI specification for the platform billing endpoints, generated directly from Layer 4's billing routes.
4. **No Forwarding Shims:** Route docstrings in Layer 4 accurately reflect local Layer 4 execution. No fake forwarding proxies exist.

### Billing ownership (final)

Billing is owned by `services/layer4-agents/`. The `contracts/openapi/layer7-billing.json` file is retained only as the authoritative OpenAPI filename for the billing endpoints exported from Layer 4; there is no `layer7` runtime, no forwarding shims, and no separate billing service.

## Compatibility Notes

- **COMPAT-L4-003:** Resolved on 2026-09-01. L4 billing routes are no longer proxies or shims; they are the sole canonical implementation. COMPAT-L4-003 is archived.
- `services/billing/` and `services/layer7-billing/` are completely decommissioned.

## Acceptance Criteria

- [x] Historical: `docker build -f services/billing/Dockerfile .` succeeded before this ADR was superseded. The Dockerfile is now retired because `services/billing/` is non-deployable.
- [x] `services/layer7-billing/` deleted and ratcheted in arch tests (`tests/arch/test_legacy_billing_removal.py`).
- [x] L4 billing route tests pass (`pytest services/layer4-agents/tests/ -k billing`).
- [x] Layer 4 billing OpenAPI contract exported at `contracts/openapi/layer7-billing.json`.
- [x] ADR-023 (this document) merged to `main`; final single-owner resolution recorded on 2026-09-01.

## Related Decisions

- ADR-010: PostgreSQL RLS for Multi-Tenancy
- ADR-017: JWT/API-Key Hybrid Authentication
- ADR-022: Layer 4 Internal Decomposition
- `docs/governance/compatibility-debt-registry.md`
- `plans/billing-dedup/plan.md`

---

**Last Updated:** October 15, 2026
