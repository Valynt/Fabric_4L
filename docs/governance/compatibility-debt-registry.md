# Compatibility Debt Registry

> **Audit note (2026-07-18):** This registry references files and namespaces that no longer exist on disk: root `value_fabric/layer3/` and `value_fabric/layer3/api/compat_wiring.py` (the root `value_fabric/` directory is gone), `apps/web/src/components/WfPrimitives.tsx`, `apps/web/src/components/ui/fabric/LoadingSkeleton.tsx`, and `docs/DEPRECATIONS.md` (now at `archive/2026-05-28/DEPRECATIONS.md`). Entries confirmed missing are struck through below; reconcile or remove them at the next review.

> **Canonical source of truth** for runtime compatibility shims, wrappers, and
> their target-removal dates. New entries land here, not in
> [`docs/DEPRECATIONS.md`](../DEPRECATIONS.md). The machine-readable mirror is
> [`deprecations.json`](deprecations.json) (regenerate from this registry;
> do not hand-edit). The CI gate input is
> [`tests/baselines/deprecation-budget.json`](../../tests/baselines/deprecation-budget.json).
> Pattern-level historical entries remain in
> [`docs/DEPRECATIONS.md`](../DEPRECATIONS.md) for traceability only.

This registry tracks **runtime** compatibility wrappers/shims that exist to preserve backward compatibility while canonical paths are adopted.

## Policy

- New runtime `legacy`/`compatibility` markers require a matching tracker entry here before merge.
- Launch freeze policy: no net-new runtime compatibility wrapper/shim file under canonical runtime roots may merge without explicit Platform Architecture approval recorded here.
- Each entry must include owner, reason, an explicit target removal date, review metadata, and a post-launch removal ticket.
- Entries are reviewed monthly and pruned when removed from runtime.

## Review Cadence

- **Last reviewed:** 2026-08-27 (billing consolidation; `services/billing` legacy package removed, COMPAT-BILL-001)
- **Next review due:** 2026-09-27
- **Review owner:** Platform Architecture

## Compatibility Gate Inventory

The unified compatibility gate runner uses the inventory below as its source of truth for
Phase 1 subcommands. Existing standalone checks remain supported and are invoked as-is.

<!-- COMPAT_GATE_INVENTORY_START -->
```json
[
	{
		"check_id": "GATE-COMPAT-001",
		"subcommand": "deprecated-namespace-imports",
		"owner": "platform-architecture",
		"command": "python scripts/ci/check_deprecated_namespace_imports.py --strict --use-baseline --json",
		"required": true,
		"scope": "repo",
		"notes": "Baseline-aware deprecated namespace import gate."
	},
	{
		"check_id": "GATE-COMPAT-002",
		"subcommand": "layer-shim-drift",
		"owner": "platform-architecture",
		"command": "python scripts/ci/check_layer1_api_main_shim_drift.py && python scripts/ci/check_layer3_settings_shim_drift.py",
		"required": true,
		"scope": "repo",
		"notes": "Layer 1 and Layer 3 shim drift checks."
	},
	{
		"check_id": "GATE-COMPAT-003",
		"subcommand": "duplicate-source-trees",
		"owner": "platform-architecture",
		"command": "python scripts/ci/check_duplicate_source_trees.py --layers layer1 layer2 layer3 layer4 layer5 layer6",
		"required": true,
		"scope": "repo",
		"notes": "Duplicate source-tree detection for shim/canonical drift."
	},
	{
		"check_id": "GATE-COMPAT-004",
		"subcommand": "frontend-shim-registration",
		"owner": "web-platform",
		"command": "pnpm --dir apps/web run check:compatibility-shims-registered",
		"required": true,
		"scope": "frontend",
		"notes": "Ensures frontend compatibility shims are registered in this document."
	},
	{
		"check_id": "GATE-COMPAT-005",
		"subcommand": "deprecated-tracer-imports",
		"owner": "platform-architecture",
		"command": "python scripts/ci/check_deprecated_tracer_imports.py",
		"required": true,
		"scope": "repo",
		"notes": "Blocks deprecated custom tracer imports."
	},
	{
		"check_id": "GATE-COMPAT-006",
		"subcommand": "shim-change-ack",
		"owner": "platform-architecture",
		"command": "python scripts/ci/check_shim_change_ack.py",
		"required": true,
		"scope": "ci",
		"notes": "Checks required labels when shim paths are changed on pull requests."
	}
]
```
<!-- COMPAT_GATE_INVENTORY_END -->

## Registry

| ID | Runtime path | Type | Owner | Reason | Target removal date | Review metadata | Post-launch removal ticket |
|---|---|---|---|---|---|---|---|
| COMPAT-L1-001 | `services/layer1-ingestion/src/layer1_ingestion/api/routes/compatibility.py` | Route wrapper | layer1-ingestion | Maintains legacy ingestion route aliases while clients move to canonical route modules. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-06-16. | PLATARCH-REMOVE-L1-001 |
| ~~COMPAT-L1-002~~ | ~~`services/layer1-ingestion/src/api/routes/compatibility.py`~~ | ~~Legacy package mirror shim~~ | ~~layer1-ingestion~~ | Removed 2026-06-24 — canonical compatibility routes now live under `services/layer1-ingestion/src/layer1_ingestion/api/routes/compatibility.py`; legacy `src.api` mirror was deleted with Layer 1 package-path migration. | ~~2026-08-31~~ | Removed ahead of schedule. | PLATARCH-REMOVE-L1-002 ✅ |
| COMPAT-L3-001 | `services/layer3-knowledge/src/api/routes/compat_aliases.py` | Route wrapper | layer3-knowledge | Keeps compatibility aliases for route naming transitions in Layer 3 APIs. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-06-16. | PLATARCH-REMOVE-L3-001 |
| COMPAT-L3-002 | `services/layer3-knowledge/src/api/routes/entity_compat.py` | Route shim | layer3-knowledge | Supports older entity endpoint patterns while frontend and SDK consumers migrate. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-06-16. | PLATARCH-REMOVE-L3-002 |
| ~~COMPAT-L3-003~~ | ~~`value_fabric/layer3/`~~ | ~~Namespace placeholder~~ | ~~layer3-knowledge~~ | ~~Retains the historical Layer 3 import namespace during shim removal.~~ **Removed/archived:** root `value_fabric/` directory no longer exists; canonical implementation is in `services/layer3-knowledge/src/`. | ~~2026-10-31~~ | Reviewed 2026-07-18 — path absent. | ~~PLATARCH-REMOVE-L3-003~~ |
| ~~COMPAT-L3-004~~ | ~~`value_fabric/layer3/api/compat_wiring.py`~~ | ~~Version compatibility wiring~~ | ~~layer3-knowledge~~ | ~~Preserves request and response transformation wiring while legacy v1 clients complete removal.~~ **Removed/archived:** file path no longer exists. | ~~2026-08-31~~ | Reviewed 2026-07-18 — path absent. | ~~PLATARCH-REMOVE-L3-004~~ |
| COMPAT-L3-005 | `services/layer3-knowledge/src/services/compat_metrics.py` | Compatibility metrics surface | layer3-knowledge | Tracks deprecated Layer 3 route and field usage until the remaining compatibility paths are removed. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-06-16. | PLATARCH-REMOVE-L3-005 |
| ~~COMPAT-L5-001~~ | ~~`value_fabric/layer5/`~~ | ~~Package shim tree~~ | ~~layer5-ground-truth~~ | Removed 2026-06-22 — canonical Layer 5 runtime now lives only under `services/layer5-ground-truth/src/layer5_ground_truth`; compatibility namespace must not be restored. | ~~2026-09-30~~ | Removed ahead of schedule; guard accepts absent tree and rejects non-shim reintroductions. | PLATARCH-REMOVE-L5-001 ✅ |
| COMPAT-L5-002 | `services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions/018_drop_legacy_model_registry_rls_policies.py` | Migration compatibility cleanup | layer5-ground-truth | Transitional migration artifact that references legacy model-registry naming while policy cleanup finishes. | 2026-09-30 | Platform Architecture approved 2026-06-16; reviewed 2026-06-16. | PLATARCH-REMOVE-L5-002 |
| ~~COMPAT-WEB-001~~ | ~~`apps/web/src/api/legacy.ts`~~ | ~~Frontend API shim~~ | ~~web-platform~~ | Removed 2026-05-14 — zero active imports confirmed; file deleted. | ~~2026-07-31~~ | Removed ahead of schedule. | PLATARCH-REMOVE-WEB-001 ✅ |
| COMPAT-WEB-002 | `apps/web/src/contexts/AuthContext.tsx` | Auth token compatibility surface | web-platform | Keeps token-shaped auth context fields while httpOnly cookie auth migration finishes. | 2027-06-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extension approved 2026-08-27 by Platform Architecture. | PLATARCH-REMOVE-WEB-002 |
| COMPAT-WEB-003 | `apps/web/src/config/auth.ts` | Provider option compatibility shim | web-platform | Legacy Microsoft provider key retained for existing tenant configs. | 2026-09-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-003 |
| COMPAT-WEB-004 | `apps/web/src/stores/userTierStore.ts` | Legacy route alias shim | web-platform | Legacy redirects retained while route canonicalization completes. | 2026-08-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-004 |
| COMPAT-WEB-005 | `apps/web/src/services/sessionService.ts` | Frontend session API shim | web-platform | Legacy session snapshot and access-token helpers retained while callers migrate to SessionMeta and cookie auth. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extended by S1-T1-CI-STABILIZE. | PLATARCH-REMOVE-WEB-005 |
| ~~COMPAT-WEB-006~~ | ~~`apps/web/src/components/AppShell.tsx`~~ | ~~Controlled state compatibility shim~~ | ~~web-platform~~ | ~~Internal fallback state remains for older callers not yet passing controlled props.~~ **Removed/archived:** `apps/web/src/components/AppShell.tsx` no longer exists. | ~~2026-08-15~~ | Reviewed 2026-08-27 — path absent. | ~~PLATARCH-REMOVE-WEB-006~~ |
| COMPAT-WEB-007 | `apps/web/src/schemas/auth.ts` | Role parsing compatibility shim | web-platform | Parser accepts frontend tier aliases in addition to canonical backend roles during migration. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extension approved 2026-08-27 by Platform Architecture. | PLATARCH-REMOVE-WEB-007 |
| ~~COMPAT-WEB-008~~ | ~~`apps/web/src/components/WfPrimitives.tsx`~~ | ~~Type alias compatibility shim~~ | ~~web-platform~~ | ~~Legacy EntityType alias retained while workflow primitive callers migrate.~~ **Removed/archived:** file does not exist in `apps/web/src/components/`. | ~~2026-07-31~~ | Reviewed 2026-07-18 — path absent. | ~~PLATARCH-REMOVE-WEB-008~~ |
| ~~COMPAT-WEB-009~~ | ~~`apps/web/src/hooks/useAgentStream.ts`~~ | ~~Hook compatibility wrapper~~ | ~~web-platform~~ | Removed 2026-06-23 — suggested-action helper moved into canonical `apps/web/src/agui/useAgentEvents.ts`; compatibility file deleted. | ~~2026-07-31~~ | Removed ahead of schedule. | PLATARCH-REMOVE-WEB-009 ✅ |
| ~~COMPAT-WEB-010~~ | ~~`apps/web/src/navigation/navHelpers.ts`~~ | ~~Type/export alias shim~~ | ~~web-platform~~ | Removed 2026-06-21 — callers and tests migrated to `apps/web/src/navigation/navigationService.ts`; shim file deleted. | ~~2026-06-30~~ | Removed ahead of schedule. | PLATARCH-REMOVE-WEB-010 ✅ |
| ~~COMPAT-WEB-011~~ | ~~`apps/web/src/components/ui/fabric/LoadingSkeleton.tsx`~~ | ~~UI component compatibility shim~~ | ~~web-platform~~ | ~~Deprecated fabric wrapper kept for callers still using legacy skeleton component.~~ **Removed/archived:** `apps/web/src/components/ui/fabric/` directory does not exist. | ~~2026-07-31~~ | Reviewed 2026-07-18 — path absent. | ~~PLATARCH-REMOVE-WEB-011~~ |
| COMPAT-WEB-012 | `apps/web/src/hooks/useBenchmarks.ts` | Type export shim | web-platform | Backward-compatible type re-export to avoid import churn; canonical types are in `apps/web/src/schemas/benchmark.ts`. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extended by S1-T1-CI-STABILIZE. | PLATARCH-REMOVE-WEB-012 |
| COMPAT-WEB-013 | `apps/web/src/hooks/useApiShared.ts` | Constant alias shim | web-platform | Backward-compatible stale-time aliases preserved for legacy hook imports. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extension approved 2026-08-27 by Platform Architecture. | PLATARCH-REMOVE-WEB-013 |
| COMPAT-WEB-014 | `apps/web/src/hooks/useFormulas.ts` | Type export shim | web-platform | Backward-compatible type re-export for formula consumers; canonical types are in `apps/web/src/schemas/formula.ts`. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extended by S1-T1-CI-STABILIZE. | PLATARCH-REMOVE-WEB-014 |
| COMPAT-WEB-015 | `apps/web/src/hooks/useGraphQuery.ts` | Hook compatibility wrapper | web-platform | Deprecated graph query hook retained while callers migrate to `useSubgraph`. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extension approved 2026-08-27 by Platform Architecture. | PLATARCH-REMOVE-WEB-015 |
| COMPAT-WEB-016 | `apps/web/src/hooks/useValuePacks.ts` | Type export shim | web-platform | Backward-compatible schema type re-export; canonical types are in `apps/web/src/schemas/valuePack.ts`. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extended by S1-T1-CI-STABILIZE. | PLATARCH-REMOVE-WEB-016 |
| COMPAT-WEB-017 | `apps/web/src/hooks/useVariables.ts` | Type export shim | web-platform | Backward-compatible type re-export for variable consumers; canonical types are in `apps/web/src/schemas/variable.ts`. | 2026-12-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19; extended by S1-T1-CI-STABILIZE. | PLATARCH-REMOVE-WEB-017 |
| COMPAT-WEB-018 | `apps/web/src/components/workspace/RightRail.tsx` | AG-UI prop compatibility shim | web-platform | Backward-compatible RightRail prop contract maintained during `useAgentEvents` rollout. | 2026-08-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-018 |
| COMPAT-WEB-019 | `apps/web/src/api/__tests__/contract/openapi-drift.contract.test.ts` | Contract test compatibility allowance | web-platform | Allows the temporary deprecated Layer 6 readiness alias while API consumers migrate to canonical readiness checks; guarded by the OpenAPI drift contract test. | 2026-08-31 | Platform Architecture approved 2026-06-05; reviewed 2026-06-05. | PLATARCH-REMOVE-WEB-019 |
| COMPAT-WEB-020 | `apps/web/src/components/ui/fabric/LegacyTabs.tsx` | UI component compatibility shim | web-platform | Retains legacy tab API surface while callers migrate to canonical tab primitives. | 2026-08-31 | Platform Architecture approved 2026-06-16; reviewed 2026-06-16. | PLATARCH-REMOVE-WEB-020 |
| COMPAT-WEB-021 | `apps/web/src/contexts/AuthContextCompat.ts` | Auth context compatibility shim | web-platform | Legacy tenant context fallback retained while canonical auth context migration completes. | 2026-12-31 | Platform Architecture approved 2026-06-25; extended by S1-T1-CI-STABILIZE. | PLATARCH-REMOVE-WEB-021 |
| COMPAT-L3-006 | `services/layer3-knowledge/src/services/compat_policy.py` | Compatibility policy shim | layer3-knowledge | Legacy context access path retained during canonical policy migration. | 2026-12-31 | Platform Architecture approved 2026-06-25; extended by S1-T1-CI-STABILIZE. | PLATARCH-REMOVE-L3-006 |
| COMPAT-L4-001 | `services/layer4-agents/src/api/routes/frontend_compat.py` | Route shim | layer4-agents | Preserves historical frontend contract during workflow API consolidation. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-06-16. | PLATARCH-REMOVE-L4-001 |
| COMPAT-L4-004 | `services/layer4-agents/src/layer4_agents/api/routes/frontend_compat.py` | Package mirror route shim | layer4-agents | Mirrors frontend compatibility route for callers using the `layer4_agents` package path while consolidation remains in progress. | 2026-08-31 | Platform Architecture approved 2026-06-16; reviewed 2026-06-16. | PLATARCH-REMOVE-L4-004 |
| ~~COMPAT-L4-002~~ | ~~`value_fabric/layer4/billing/`~~ | ~~Canonical runtime shim~~ | ~~layer4-agents~~ | ~~Re-exports billing domain from the Layer 4 monolith during extraction.~~ **Removed/archived:** root `value_fabric/` directory no longer exists; canonical deployable billing behavior is `services/layer7-billing/`. | ~~2026-09-30~~ | Reviewed 2026-08-22 — path absent. | ~~PLATARCH-REMOVE-L4-002~~ |
| COMPAT-L4-003 | `services/layer4-agents/src/layer4_agents/api/routes/billing.py` | Service proxy shim | layer4-agents | Existing L4 billing routes are thin forwarding shims to Layer 7 billing during caller migration. Removal target when all callers migrate directly to `services/layer7-billing/`. | 2026-10-31 | Platform Architecture approved 2026-05-22; reviewed 2026-06-05 for S3-4 billing consolidation. | PLATARCH-REMOVE-L4-003 |
| ~~COMPAT-BILL-001~~ | ~~`services/billing/`~~ | ~~Legacy non-deployable billing package~~ | ~~billing-owner~~ | ~~Duplicate money-domain knowledge retained only for historical Stripe migration + webhook-idempotency regression coverage. Canonical runtime is `services/layer7-billing/`.~~ **Removed/archived:** entire `services/billing/` package deleted 2026-08-27 (COMPAT-BILL-001) — zero production consumers. Plans/usage/invoices/payment-state owned by `services/layer7-billing/`; Stripe customer/subscription/webhook domain owned by `services/layer4-agents/src/layer4_agents/services/billing_service.py`. | ~~2026-10-31~~ | Reviewed 2026-08-27 — path absent. | ~~PLATARCH-REMOVE-BILL-001~~ |
## Known Intentional Behaviors (Not Shims)

These are deliberate v1 design decisions that raise errors rather than silently degrading. They are documented here to prevent future "fixes" that would weaken the intended behavior.

### Vault config source — `VaultSourceNotSupportedError`

| Field | Value |
|---|---|
| **Location** | `services/layer3-knowledge/src/config/manager.py` — `ConfigurationManager._load_from_vault()` |
| **Behavior** | Raises `VaultSourceNotSupportedError` (a `RuntimeError` subclass) when a `ConfigSource` with `type: vault` is loaded. |
| **Intentional since** | v1 |
| **Rationale** | Direct Vault API access via `hvac` is not implemented. Silently returning an empty dict would cause misconfigured services to start with missing secrets, which is worse than a hard failure. |
| **Migration path** | Use External Secrets Operator (ESO) to sync Vault secrets into Kubernetes Secrets, then mount them as environment variables. Change the `ConfigSource` to `type: env`. See `docs/secrets-management.md`. |
| **Test coverage** | `services/layer3-knowledge/tests/test_vault_config_source.py` (7 tests, all passing — verified Sprint 6 2026-05-18) |
| **Do not "fix" by** | Returning `{}`, catching the exception silently, or adding a partial `hvac` integration without a full secrets-management review. |

### Presidio dependency hold — `presidio-analyzer` / `presidio-anonymizer` pinned at 2.2.362

| Field | Value |
|---|---|
| **Location** | `services/layer1-ingestion/pyproject.toml` + `requirements.txt` (held `==2.2.362`); guarded in `.github/dependabot.yml` layer1 pip block (`ignore: >=2.2.363`) |
| **Behavior** | `presidio-analyzer` and `presidio-anonymizer` are held at 2.2.362 because subsequent releases impose a `cryptography` upper bound incompatible with Fabric's security-required `cryptography>=50.0.0`. |
| **Evidence** | `presidio-anonymizer 2.2.364` requires `cryptography<49.0.0,>=48.0.1`; `2.2.363` requires `<47`; `2.2.362` allows `>=46.0.4` with no upper bound. The 2.2.363+ caps force `cryptography` below the GHSA-g6cj-pr64-35w5 fix floor (50.0.0). |
| **Intentional since** | 2026 (platform crypto baseline `>=50.0.0` established) |
| **Migration path** | Remove the `==2.2.362` hold **and** the Dependabot ignore entry only after a Presidio release supports the platform cryptography baseline (`cryptography>=50.0.0`). This is an upstream compatibility constraint (museum security floor ahead of Presidio's dependency ceiling), not a bug in the hold. |
| **Test coverage** | Layer 1 install resolution (`pip install -e services/layer1-ingestion`) + `pip check` both pass with `cryptography>=50.0.0` resolved. |
| **Do not "fix" by** | Bumping Presidio to 2.2.363/2.2.364, downgrading `cryptography` below 50.0.0, or permanently ignoring all Presidio releases. |

---

## Post-Migration Debt Items (2026-05-27)

### Layer 3 namespace package shim causes `db.query_execution` relative import failure

| Field | Value |
|---|---|
| **ID** | DEBT-L3-IMPORT-001 |
| **Title** | Layer 3 namespace package shim causes `db.query_execution` relative import failure |
| **Evidence** | Importing `value_fabric.layer3.api.main` fails because `services/layer3-knowledge/src/db/query_execution.py` raises `ImportError: attempted relative import beyond top-level package` when resolving `from ..graph.query_guards import ...`. |
| **Impact** | Blocks full Layer 3 app import smoke test; blocks Layer 3 test suite import via `conftest.py`; prevents full validation of the `create_fabric_app` migration despite `py_compile` passing. |
| **Status** | Pre-existing, unrelated to `create_fabric_app` migration. |
| **Priority** | P1 — blocks CI confidence for Layer 3. |
| **Decision** | Do not mark Layer 3 as fully validated until this issue is fixed or bypassed with an agreed test shim. Track separately from the factory migration. |

### Layer 3 `add_rate_limiting` instantiates `RateLimitMiddleware` without `app.add_middleware` registration

| Field | Value |
|---|---|
| **ID** | DEBT-L3-RATELIMIT-001 |
| **Title** | Layer 3 `add_rate_limiting` instantiates `RateLimitMiddleware` without `app.add_middleware` registration |
| **Evidence** | Existing `add_rate_limiting` behavior creates `RateLimitMiddleware(app)` but does not register it with `app.add_middleware` or `app.middleware("http")`. The return value is discarded in `main.py`. |
| **Impact** | Possible no-op or nonstandard middleware registration pattern; runtime rate limiting may not be actively intercepting requests. |
| **Status** | Pre-existing behavior preserved intentionally during `create_fabric_app` migration. |
| **Priority** | P1/P2 depending on whether runtime tests prove rate limiting works. |
| **Decision** | Do not fix this inside the `create_fabric_app` migration unless specifically scoped. Track it separately. If runtime validation shows rate limiting is nonfunctional, escalate to P1 and schedule a fix. |

## Monthly Prune Procedure

1. Run `pytest tests/ci/test_compatibility_debt_registry.py`.
2. For each listed path, confirm whether the shim/wrapper still exists and is still required.
3. Remove entries that are no longer present in runtime code.
4. Update `Last reviewed` and `Next review due` dates.
5. If any target date has passed, either remove the shim or add a dated extension note in this file.

## Layer 3 Source Ownership and Exceptions

- **Canonical owner/path:** `services/layer3-knowledge/src` (Layer 3 runtime implementation).
- **Compatibility owner/path:** `value_fabric/layer3` as a namespace placeholder during shim removal.
- **Allowed compatibility content:** `value_fabric/layer3/__init__.py` plus explicitly registered compatibility shims only.
- **Guardrail:** `scripts/ci/check_layer3_wrapper_drift.py` fails if runtime Python files are reintroduced under the compatibility namespace.



## Frontend Shim Inventory (apps/web/src)

| Shim path | Canonical replacement path | Current callers (2026-05-18 sweep) | Risk tier | Target removal milestone |
|---|---|---|---|---|
| `apps/web/src/services/sessionService.ts` (`getSessionSnapshot`/`persistSession` family) | `SessionMeta` APIs in `apps/web/src/services/sessionService.ts` | **Removed on 2026-05-18** (no runtime callers) | Low | Completed in Sprint 6 (2026-05-18) |
| ~~`apps/web/src/hooks/useAgentStream.ts`~~ | `apps/web/src/agui/useAgentEvents.ts` | Removed 2026-06-23 — default actions helper now lives in `useAgentEvents.ts`; no compatibility caller remains. | ~~Medium~~ | Completed 2026-06-23 |
| ~~`apps/web/src/navigation/navHelpers.ts`~~ | `apps/web/src/navigation/navigationService.ts` | Removed 2026-06-21 — tests now import `navigationService.ts` directly; no runtime callers remain. | Low | Completed 2026-06-21 |
| `apps/web/src/components/ui/fabric/LoadingSkeleton.tsx` | `apps/web/src/components/ui/skeleton.tsx`, `apps/web/src/components/ui/SkeletonViews.tsx` | `apps/web/src/components/ui/fabric/index.ts` and downstream fabric imports | Low | Sprint 7 UI primitive migration |
| `apps/web/src/components/blocks/SectionCard.tsx` (`subtitle` alias) | `description` prop on same component | Pages still passing `subtitle` (e.g., `pages/value-case/ValueCasePage.tsx`) | Low | Sprint 7 card-prop cleanup |
| `apps/web/src/hooks/useApiShared.ts` (legacy stale-time aliases) | Canonical `STALE_TIME` keys in same module | shared hook consumers across `apps/web/src/hooks/` | Medium | Sprint 8 hooks API freeze |
| `apps/web/src/config/auth.ts` (legacy Microsoft option) | Canonical auth provider configuration in same module | auth config consumers via `authProviders` | Medium | Sprint 8 tenant config migration |
| `apps/web/src/stores/userTierStore.ts` (legacy redirects) | canonical route map in same store/module | navigation flows that still hit legacy routes | Medium | Sprint 8 route canonicalization |
| `apps/web/src/stores/index.ts` (`Entity` re-export alias) | `EntityData` from `apps/web/src/hooks/useEntities.ts` (already re-exported in same file) | Ontology Browser and other store-index consumers importing `Entity` from `@/stores` | Low | Sprint 7 store export cleanup |

## Frontend Compatibility Shim Migration Runbook

1. **Identify shim usage**: run `rg -n "<alias-or-deprecated-api>" apps/web/src` and collect all callsites.
2. **Switch to canonical API**: replace alias imports/props/hooks with canonical path from this registry, then update nearby tests in the same feature slice.
3. **Verify no remaining callers**: rerun `rg` to confirm zero callsites outside approved shim files.
4. **Remove shim code**: delete deprecated wrapper/alias paths and compatibility tests that only validated shim behavior.
5. **Update registry + CI evidence**: mark the entry removed (strikethrough row), include removal date, and run `pnpm --dir apps/web run check:compatibility-shims-registered`.

## Value Fabric Import Boundary Migration (2026-05-26; public facade removed 2026-05-29)

- Public API entrypoint `value_fabric.public_api.shared` was removed after runtime consumers migrated to canonical `value_fabric.shared.*` imports.
- Service-local adapter modules remain under each layer service at `src/.../adapters/value_fabric_api.py`.
- CI guardrail `scripts/ci/check_value_fabric_public_imports.py` now blocks runtime imports of `value_fabric.public_api` and reports remaining non-adapter shared deep imports for migration tracking.

### Remaining direct deep-import counts (non-test runtime files)

- `services/layer1-ingestion`: 108
- `services/layer2-extraction`: 112
- `services/layer3-knowledge`: 161
- `services/layer4-agents`: 56
- `services/layer5-ground-truth`: 27
- `services/layer6-benchmarks`: 16

Migration policy: runtime imports of `value_fabric.public_api` are blocked; existing non-adapter `value_fabric.shared.*` deep imports remain migration inventory until each service is migrated to adapter imports.

## Lint Debt: Relative Parent Imports (TID252)

**Status:** Ignored at service level; requires dedicated migration pass

**Services affected:**
- `services/layer1-ingestion`: 220 TID252 relative parent imports (e.g. `from ..crawler import ...`) — ignored in `pyproject.toml` as of 2026-06-01
- `services/layer2-extraction`: ~230 TID252 occurrences (not yet catalogued)
- `services/layer3-knowledge`: 479 TID252 relative parent imports — ignored in `pyproject.toml` as of 2026-06-01

**Rationale:** Converting `from ..module` to absolute `from src.layer.module` requires verifying each changed import path resolves correctly in both dev and production runtime contexts. A bulk migration risks runtime `ModuleNotFoundError` in Docker or pytest importlib mode.

**Recommended approach:** Per-service migration with before/after startup tests. Target removal date should be set per service after owner review.

**Tracking ticket:** `PLATARCH-TID252-MIGRATION` (to be created)
