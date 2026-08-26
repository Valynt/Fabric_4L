# Product Contract — FABRIC_4L | VALUEPILOT

This directory is the cross-functional source of truth for Product, Design, Engineering, Data and AI, Governance, Security, and QA. It is the maintained, split-artifact form of the monolithic Master Product Intent (see `10_changelog.md`).

## Authority: intent overrides implementation

This pack defines the required target experience. Existing code, mock journeys, legacy routes, seeded data, or implementation shortcuts do not override it. A mismatch is a tracked product gap, not an alternate interpretation.

- Deviations from this contract MUST be recorded in `09_gap-register.md` as `GAP-xx` entries with priority, current implementation, and required convergence.
- A code change that exposes an unresolved deviation MUST reference a gap ID, owner, severity, containment, and target disposition.
- Changes to this contract follow the change-governance rules in `07_engineering-contract.md`.

## Files

| File | Content |
|---|---|
| `01_product-intent.md` | Vision, promise, north-star, principles, non-goals, normative rules R-1..R-8 |
| `02_users-and-jobs.md` | Personas, jobs-to-be-done, success measures |
| `03_domain-lifecycle.md` | Canonical domain chain, artifact authority, source-of-truth hierarchy, state dimensions |
| `04_canonical-journey.md` | Journey stages J-1..J-10 with Entry/Action/System/Exit and frontend surfaces |
| `05_experience-contract.md` | UX shell rules, state behavior, review gates, provenance, accessibility |
| `06_user-stories.md` | Story catalogue VP-01..VP-14 |
| `07_engineering-contract.md` | Service responsibilities, invariants, evidence/fallback policy, NFRs, source anchors |
| `08_definition-of-done.md` | Cross-functional Definition of Done |
| `09_gap-register.md` | Gap register GAP-01..GAP-12, delivery sequence, convergence decisions |
| `10_changelog.md` | Contract changelog |

## Stable IDs

All cross-references use stable, machine-resolvable IDs. Prose mentions of IDs MUST resolve in `control-plane/contract_manifest.yaml`.

| Prefix | Namespace | Defined in |
|---|---|---|
| `R-n` | Normative product rules (R-1..R-8) | `01_product-intent.md` |
| `VP-xx` | User stories (VP-01..VP-14) | `06_user-stories.md` |
| `GAP-xx` | Product gaps (GAP-01..GAP-12) | `09_gap-register.md` |
| `J-n` | Canonical journey stages (J-1..J-10) | `04_canonical-journey.md` |
| `BEH-xx` | Behavior cards (BEH-01..BEH-09, aligned to journey order) | `control-plane/behaviors/` |
| `AG-0x` / `CTRL-xx` / `EV-x` | Release gates, controls, evidence types | `control-plane/release/` |

Normative vocabulary: **MUST** = required for customer-ready release; **SHOULD** = expected unless an approved exception exists; **MAY** = optional behavior that cannot weaken a MUST.
