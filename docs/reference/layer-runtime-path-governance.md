---
title: "Layer Runtime Path Governance Matrix"
category: "reference"
audience: "contributors"
last-reviewed: "2026-06-22"
freshness: "current"
related: ["../source-tree-canonicalization", "service-routing-and-api-version-matrix", "../../AGENTS", "../getting-started/quickstart"]
---

# Layer Runtime Path Governance Matrix

This reference is the canonical contribution guide for **where new code must be added** per platform layer.

Use this before creating files so we avoid drift into archived, compatibility-only, or wrapper-only paths.

## Policy

- **Canonical runtime paths** are the source of truth for business logic and runtime modules.
- **Legacy/compatibility paths** are historical unless explicitly listed as active; removed paths must not be restored.
- **Allowed new development target** is the only approved destination for net-new logic.
- **Deprecation owner/date** identifies who governs removal or further migration.

## Layer path matrix

| Layer | Canonical runtime paths | Legacy / compatibility paths (no net-new logic) | Allowed new development target | Deprecation owner / date |
| :---- | :---------------------- | :---------------------------------------------- | :----------------------------- | :----------------------- |
| Layer 1 — Ingestion | `services/layer1-ingestion/src/` | none; `value_fabric/layer1/` removed | `services/layer1-ingestion/src/` | Layer 1 Maintainers — shim removal completed **2026-06-22** |
| Layer 2 — Extraction | `services/layer2-extraction/src/` | none; `value_fabric/layer2/` removed | `services/layer2-extraction/src/` | Layer 2 Maintainers — shim removal completed **2026-06-22** |
| Layer 3 — Knowledge Graph | `services/layer3-knowledge/src/` | none; `value_fabric/layer3/` removed | `services/layer3-knowledge/src/` | Layer 3 Maintainers — shim removal completed **2026-06-22** |
| Layer 4 — Agents | `services/layer4-agents/src/` | none; `value_fabric/layer4/` removed | `services/layer4-agents/src/` | Layer 4 Maintainers — shim removal completed **2026-06-22** |
| Layer 5 — Ground Truth | `services/layer5-ground-truth/src/layer5_ground_truth/` | none; `value_fabric/layer5/` removed | `services/layer5-ground-truth/src/layer5_ground_truth/` | Layer 5 Maintainers — shim removal completed **2026-06-22** |
| Layer 6 — Benchmarks | `services/layer6-benchmarks/src/` | none; `value_fabric/layer6/` removed | `services/layer6-benchmarks/src/` | Layer 6 Maintainers — shim removal completed **2026-06-22** |

## Adjacent service path matrix

Signal refinement and billing are deployable bounded capabilities, not additional
horizontal core pipeline layers. They must communicate with the six core layers
through contracted HTTP/client boundaries and must not import non-adjacent service
runtime modules directly.

| Capability | Canonical runtime paths | Legacy / compatibility paths (no net-new logic) | Allowed new development target | Owner / review |
| :--------- | :---------------------- | :---------------------------------------------- | :----------------------------- | :------------- |
| Signal Refinery | `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/` | none approved outside service-local wrappers | `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/` | Signal Refinery Maintainers |
| Billing | `services/layer7-billing/src/layer7_billing/` | Legacy `services/billing/` removed 2026-08-27 (COMPAT-BILL-001); membership domain owned by `services/layer4-agents/src/layer4_agents/services/billing_service.py` | `services/layer7-billing/src/layer7_billing/` | Billing Maintainers |

Layer 6 note: when compatibility wrappers are present under `services/layer6-benchmarks/src/`, they are wrapper-only and cannot contain local domain logic; CI enforces this via `scripts/ci/check_layer6_wrapper_drift.py`, and `scripts/check_mirrored_files.py` enforces byte-alignment against the manifest-declared wrapper template in `scripts/mirrored_files.json`.

## Cross-root import policy (allowed vs forbidden)

### Allowed imports in production/runtime code

- Runtime-to-runtime imports within canonical roots (for example `services/layer3-knowledge/src/*`, `value_fabric.shared.identity.*` via `packages/shared/src/value_fabric/shared/identity/*`, and `services/layer5-ground-truth/src/layer5_ground_truth/*`).
- Compatibility imports that remain inside approved service-local compatibility wrappers documented in this matrix.
- Adjacent service clients that call another service through an explicit HTTP/client adapter and do not import the target service's runtime modules.

### Forbidden imports in production/runtime code

- Any import from `prototypes/`.
- Any import from `docs/archive/`.
- Any import from other non-runtime roots that are not canonical runtime or approved compatibility wrapper paths.
- Direct imports from another service runtime root when a contracted client boundary should be used instead.

These restrictions are enforced by architecture tests (`tests/arch/test_no_non_runtime_imports.py`) and frontend hygiene linting (`apps/web/scripts/quality/assert-frontend-hygiene.mjs`).


## Shared identity package canonical location

- **Canonical runtime package location (only):** `packages/shared/src/value_fabric/shared/identity/`.
- **Approved public import root:** `value_fabric.shared.identity`.
- **Disallowed imports:** `shared.identity.*`, any `value_fabric.layer*/identity*` module, and any service-local `...identity...` module outside approved shims.
- **CI guardrail:** `scripts/ci/check_shared_identity_canonical_imports.py` with explicit shim exceptions in `config/ci/shared_identity_import_shim_allowlist.txt`.
- **Policy:** no alternate canonical paths are allowed for shared identity runtime code.

## Contributor checklist (required)

Before opening a PR with backend runtime changes:

1. Confirm the target layer in this matrix.
2. Add net-new logic only to the canonical runtime path.
3. Keep service wrapper changes minimal and wiring-only.
4. If compatibility code is touched, add a TODO with migration intent and owner.

## Layer 3 settings module ownership

- **Canonical settings module:** `services/layer3-knowledge/src/config/settings.py`.
- **Compatibility namespace:** `value_fabric/layer3/` is a namespace placeholder only; do not add a duplicate settings shim there.
- **CI drift guardrail:** `scripts/ci/check_layer3_settings_shim_drift.py` via `.github/workflows/layer3-wrapper-drift.yml`.

## Layer 3 app_monolith ownership note

- Canonical runtime route modules: `services/layer3-knowledge/src/api/routes/`.
- Legacy compatibility surface: `services/layer3-knowledge/src/api/app_monolith.py` may expose only approved compatibility delegates such as tenant-resolution helpers; do not add route handlers or endpoint logic there.
- CI guardrails: `scripts/ci/check_l3_monolith_freeze.py` and `services/layer3-knowledge/scripts/check_runtime_shim_drift.py`.

## Layer 3 API model ownership note

- Canonical implementation: `services/layer3-knowledge/src/api/models.py`.
- Compatibility namespace: `value_fabric/layer3/` must not grow a duplicate `api/models.py`; the service tree owns Layer 3 Pydantic model implementations.


## Layer 3 backup ownership boundary

- Canonical implementation: `services/layer3-knowledge/src/backup/`.
- Compatibility namespace: `value_fabric/layer3/` must not grow duplicate backup modules.
- CI guardrail: `services/layer3-knowledge/scripts/check_runtime_shim_drift.py`.


## Required parity checkpoints (CI-enforced)

The CI suite validates canonical/runtime parity for each layer (`layer1`–`layer6`) across these checkpoints:

- **Route module parity:** maintained service route modules must re-export canonical route modules (shim-only behavior).
- **Service entrypoint parity:** maintained service entrypoints must expose `app` and serve non-empty OpenAPI contracts at `/openapi.json`.
- **Middleware chain anchor parity:** each layer declares a canonical middleware anchor module that must remain present.
- **Service/repository interface parity:** each layer declares canonical service and repository interface anchor files that must remain present and referenced by parity rules.

These checkpoints are asserted by:

- `tests/contract/test_layer_runtime_parity.py`
- `tests/contract/test_layer_service_entrypoint_smoke.py`

When adding or moving canonical modules, update parity rules in these tests in the same change to avoid drift.

## Related documentation

- [Repository Agent Rules (root)](../../AGENTS.md)
- [Source Tree Canonicalization](../source-tree-canonicalization.md)
- [Service Routing and API Version Matrix](./service-routing-and-api-version-matrix.md)
- [Quickstart](../getting-started/quickstart.md)

## Architecture sentinel map maintenance

`tests/arch/test_canonical_module_sentinels.py` intentionally tracks a small, high-impact
set of canonical module pairs.

When adding a new sentinel:

1. Prefer modules that are architectural choke points (for example shared API models or boundary schemas).
2. Add one `canonical_path` + `compatibility_path` pair to `SENTINELS`.
3. Keep compatibility module behavior shim-only (re-export/delegate); do not add local classes/functions there.
4. If a compatibility module temporarily needs local logic, document the migration exception in the test file with owner and removal date before merging.

Avoid adding low-value or highly volatile modules to keep this guardrail low-noise.


## Layer 4 namespace policy

- **Authoritative import namespace:** `layer4_agents.*`.
- **Removed compatibility namespace:** `value_fabric.layer4.*` (do not restore; no net-new imports).
- **CI guardrail:** `scripts/ci/check_layer4_canonical_imports.py` with test coverage in `tests/ci/test_check_layer4_canonical_imports.py`.
