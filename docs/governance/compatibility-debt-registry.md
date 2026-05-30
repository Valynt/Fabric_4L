# Compatibility Debt Registry

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

- **Last reviewed:** 2026-05-12 (updated for Layer 3 shim-only inventory, shim conflict cleanup, and exception audit)
- **Next review due:** 2026-06-12
- **Review owner:** Platform Architecture

## Registry

| ID | Runtime path | Type | Owner | Reason | Target removal date | Review metadata | Post-launch removal ticket |
|---|---|---|---|---|---|---|---|
| COMPAT-L1-001 | `services/layer1-ingestion/src/api/routes/compatibility.py` | Route wrapper | layer1-ingestion | Maintains legacy ingestion route aliases while clients move to canonical route modules. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L1-001 |
| COMPAT-L3-001 | `value_fabric/layer3/api/routes/compat_aliases.py` | Route wrapper | layer3-knowledge | Keeps compatibility aliases for route naming transitions in Layer 3 APIs. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L3-001 |
| COMPAT-L3-002 | `value_fabric/layer3/api/routes/entity_compat.py` | Route shim | layer3-knowledge | Supports older entity endpoint patterns while frontend and SDK consumers migrate. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L3-002 |
| COMPAT-L3-003 | `services/layer3-knowledge/src/` | Package shim tree | layer3-knowledge | Compatibility re-export tree for mirrored runtime modules; canonical implementation now lives in `value_fabric/layer3` and is enforced by `scripts/ci/check_layer3_source_mirror.py`. Service-local exceptions (`api/`, `agents/`, `cache/`, `docs/`, `metrics/`, top-level `config.py`, migrations) are intentionally non-shim and tracked in `docs/governance/layer3-service-source-inventory.md` with owner/date reaffirmed in the 2026-05-12 inventory sweep. | 2026-10-31 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L3-003 |
| COMPAT-L3-004 | `value_fabric/layer3/api/compat_wiring.py` | Version compatibility wiring | layer3-knowledge | Preserves request and response transformation wiring while legacy v1 clients complete removal. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L3-004 |
| COMPAT-L3-005 | `value_fabric/layer3/services/compat_metrics.py` | Compatibility metrics surface | layer3-knowledge | Tracks deprecated Layer 3 route and field usage until the remaining compatibility paths are removed. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L3-005 |
| COMPAT-L5-001 | `value_fabric/layer5/` | Package shim tree | layer5-ground-truth | Compatibility re-export tree that delegates to canonical `services/layer5-ground-truth/src/layer5_ground_truth`. | 2026-09-30 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L5-001 |
| ~~COMPAT-WEB-001~~ | ~~`apps/web/src/api/legacy.ts`~~ | ~~Frontend API shim~~ | ~~web-platform~~ | Removed 2026-05-14 — zero active imports confirmed; file deleted. | ~~2026-07-31~~ | Removed ahead of schedule. | PLATARCH-REMOVE-WEB-001 ✅ |
| COMPAT-WEB-002 | `apps/web/src/contexts/AuthContext.tsx` | Auth token compatibility surface | web-platform | Keeps token-shaped auth context fields while httpOnly cookie auth migration finishes. | 2026-07-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-002 |
| COMPAT-WEB-003 | `apps/web/src/config/auth.ts` | Provider option compatibility shim | web-platform | Legacy Microsoft provider key retained for existing tenant configs. | 2026-09-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-003 |
| COMPAT-WEB-004 | `apps/web/src/stores/userTierStore.ts` | Legacy route alias shim | web-platform | Legacy redirects retained while route canonicalization completes. | 2026-08-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-004 |
| COMPAT-WEB-005 | `apps/web/src/services/sessionService.ts` | Frontend session API shim | web-platform | Legacy session snapshot and access-token helpers retained while callers migrate to SessionMeta and cookie auth. | 2026-06-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-005 |
| COMPAT-WEB-006 | `apps/web/src/components/AppShell.tsx` | Controlled state compatibility shim | web-platform | Internal fallback state remains for older callers not yet passing controlled props. | 2026-08-15 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-006 |
| COMPAT-WEB-007 | `apps/web/src/schemas/auth.ts` | Role parsing compatibility shim | web-platform | Parser accepts frontend tier aliases in addition to canonical backend roles during migration. | 2026-07-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-007 |
| COMPAT-WEB-008 | `apps/web/src/components/WfPrimitives.tsx` | Type alias compatibility shim | web-platform | Legacy EntityType alias retained while workflow primitive callers migrate. | 2026-07-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-008 |
| COMPAT-WEB-009 | `apps/web/src/hooks/useAgentStream.ts` | Hook compatibility wrapper | web-platform | Deprecated hook retained while callers migrate to canonical `@/agui/useAgentEvents`. | 2026-07-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-009 |
| COMPAT-WEB-010 | `apps/web/src/navigation/navHelpers.ts` | Type/export alias shim | web-platform | Re-export shim during navigation service migration. Canonical exports live in `apps/web/src/navigation/navigationService.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-010 |
| COMPAT-WEB-011 | `apps/web/src/components/ui/fabric/LoadingSkeleton.tsx` | UI component compatibility shim | web-platform | Deprecated fabric wrapper kept for callers still using legacy skeleton component. | 2026-07-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-011 |
| COMPAT-WEB-012 | `apps/web/src/hooks/useBenchmarks.ts` | Type export shim | web-platform | Backward-compatible type re-export to avoid import churn; canonical types are in `apps/web/src/schemas/benchmark.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-012 |
| COMPAT-WEB-013 | `apps/web/src/hooks/useApiShared.ts` | Constant alias shim | web-platform | Backward-compatible stale-time aliases preserved for legacy hook imports. | 2026-07-15 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-013 |
| COMPAT-WEB-014 | `apps/web/src/hooks/useFormulas.ts` | Type export shim | web-platform | Backward-compatible type re-export for formula consumers; canonical types are in `apps/web/src/schemas/formula.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-014 |
| COMPAT-WEB-015 | `apps/web/src/hooks/useGraphQuery.ts` | Hook compatibility wrapper | web-platform | Deprecated graph query hook retained while callers migrate to `useSubgraph`. | 2026-07-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-015 |
| COMPAT-WEB-016 | `apps/web/src/hooks/useValuePacks.ts` | Type export shim | web-platform | Backward-compatible schema type re-export; canonical types are in `apps/web/src/schemas/valuePack.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-016 |
| COMPAT-WEB-017 | `apps/web/src/hooks/useVariables.ts` | Type export shim | web-platform | Backward-compatible type re-export for variable consumers; canonical types are in `apps/web/src/schemas/variable.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-017 |
| COMPAT-WEB-018 | `apps/web/src/components/workspace/RightRail.tsx` | AG-UI prop compatibility shim | web-platform | Backward-compatible RightRail prop contract maintained during `useAgentEvents` rollout. | 2026-08-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-018 |
| COMPAT-L4-001 | `services/layer4-agents/src/layer4_agents/api/routes/frontend_compat.py` | Route shim | layer4-agents | Preserves historical frontend contract during workflow API consolidation. | 2026-08-31 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-L4-001 |
| COMPAT-L4-002 | `value_fabric/layer4/billing/` | Canonical runtime shim | layer4-agents | Re-exports billing domain from layer4-agents monolith during pilot extraction. Canonical implementations will move to `services/billing/src/` when service wrapper is operational. | 2026-09-30 | Platform Architecture approved 2026-05-22; reviewed 2026-05-22. | PLATARCH-REMOVE-L4-002 |
| COMPAT-L4-003 | `services/layer4-agents/src/layer4_agents/api/routes/billing.py` (future proxy) | Service proxy shim | layer4-agents | After `services/billing/` is operational, existing L4 billing routes will become thin HTTP proxies to the billing service. Removal target when all callers migrate directly. | 2026-10-31 | Platform Architecture approved 2026-05-22; reviewed 2026-05-22. | PLATARCH-REMOVE-L4-003 |
| COMPAT-SDK-001 | `sdk/python/src/valuefabric/cli/workflows.py` | CLI compatibility surface | sdk | Backward-compatible CLI workflow commands pending full canonical command migration. | 2026-09-30 | Platform Architecture approved 2026-05-12; reviewed 2026-05-12. | PLATARCH-REMOVE-SDK-001 |
| COMPAT-WEB-002 | `apps/web/src/services/sessionService.ts` | Frontend session API shim | web-platform | Legacy `SessionSnapshot` / `getSessionSnapshot` / `persistSession` compatibility wrappers were removed on 2026-05-18; remaining shim is `getAccessToken()` null-return helper while cookie auth migration finishes. Canonical API is `SessionMeta` via `getSessionMeta()`/`persistSessionMeta()`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-002 |
| COMPAT-WEB-003 | `apps/web/src/hooks/useAgentStream.ts` | Hook compatibility wrapper | web-platform | Deprecated hook retained while callers migrate to canonical `@/agui/useAgentEvents`. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-003 |
| COMPAT-WEB-004 | `apps/web/src/navigation/navHelpers.ts` | Type/export alias shim | web-platform | Re-export shim during navigation service migration. Canonical exports live in `apps/web/src/navigation/navigationService.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-004 |
| COMPAT-WEB-005 | `apps/web/src/hooks/useApiShared.ts` | Constant alias shim | web-platform | Backward-compatible stale-time aliases preserved for legacy hook imports; canonical keys are the non-legacy names in the same module. | 2026-07-15 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-005 |
| COMPAT-WEB-006 | `apps/web/src/hooks/useBenchmarks.ts` | Type export shim | web-platform | Backward-compatible type re-export to avoid import churn; canonical types are in `apps/web/src/schemas/benchmark.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-006 |
| COMPAT-WEB-007 | `apps/web/src/hooks/useFormulas.ts` | Type export shim | web-platform | Backward-compatible type re-export for formula consumers; canonical types are in `apps/web/src/schemas/formula.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-007 |
| COMPAT-WEB-008 | `apps/web/src/hooks/useVariables.ts` | Type export shim | web-platform | Backward-compatible type re-export for variable consumers; canonical types are in `apps/web/src/schemas/variable.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-008 |
| COMPAT-WEB-009 | `apps/web/src/hooks/useValuePacks.ts` | Type export shim | web-platform | Backward-compatible schema type re-export; canonical types are in `apps/web/src/schemas/valuePack.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-009 |
| COMPAT-WEB-010 | `apps/web/src/components/ui/fabric/LoadingSkeleton.tsx` | UI component compatibility shim | web-platform | Deprecated fabric wrapper kept for callers still using legacy skeleton component. Canonical replacements: `@/components/ui/skeleton` and `@/components/ui/SkeletonViews`. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-010 |
| COMPAT-WEB-011 | `apps/web/src/components/blocks/SectionCard.tsx` | Prop alias shim | web-platform | `subtitle` alias retained for backward compatibility while callers migrate to canonical `description` prop. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-011 |
| COMPAT-WEB-012 | `apps/web/src/components/AppShell.tsx` | Controlled/uncontrolled state shim | web-platform | Internal fallback state remains for older callers not yet passing controlled props. Canonical usage is controlled props from workspace shells. | 2026-08-15 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-012 |
| COMPAT-WEB-013 | `apps/web/src/components/workspace/RightRail.tsx` | AG-UI prop compatibility shim | web-platform | Backward-compatible RightRail prop contract maintained during `useAgentEvents` rollout. | 2026-08-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-013 |
| COMPAT-WEB-014 | `apps/web/src/config/auth.ts` | Provider option compatibility shim | web-platform | Legacy Microsoft provider key retained for existing tenant configs. Canonical provider list is managed via current auth provider config. | 2026-09-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-014 |
| COMPAT-WEB-015 | `apps/web/src/schemas/auth.ts` | Role parsing compatibility shim | web-platform | Parser accepts frontend tier aliases in addition to canonical backend roles to prevent auth payload drift during migration. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-015 |
| COMPAT-WEB-016 | `apps/web/src/stores/userTierStore.ts` | Legacy route alias shim | web-platform | Legacy route redirects retained while route canonicalization completes. | 2026-08-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-016 |
| COMPAT-WEB-017 | `apps/web/src/stores/index.ts` | Type re-export compatibility shim | web-platform | `Entity` type is re-exported from hooks for Ontology Browser compatibility while callers migrate to canonical `EntityData` alias in the same module export surface. | 2026-07-31 | Platform Architecture approved 2026-05-19; reviewed 2026-05-19. | PLATARCH-REMOVE-WEB-017 |

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

---

| COMPAT-WEB-002 | `apps/web/src/services/sessionService.ts` | Frontend session API shim | web-platform | Legacy `SessionSnapshot` / `getSessionSnapshot` / `persistSession` compatibility wrappers were removed on 2026-05-18; remaining shim is `getAccessToken()` null-return helper while cookie auth migration finishes. Canonical API is `SessionMeta` via `getSessionMeta()`/`persistSessionMeta()`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-002 |
| COMPAT-WEB-003 | `apps/web/src/hooks/useAgentStream.ts` | Hook compatibility wrapper | web-platform | Deprecated hook retained while callers migrate to canonical `@/agui/useAgentEvents`. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-003 |
| ~~COMPAT-WEB-004~~ | ~~`apps/web/src/navigation/navHelpers.ts`~~ | ~~Type/export alias shim~~ | ~~web-platform~~ | Removed 2026-05-19 — callers migrated to `apps/web/src/navigation/navigationService.ts`; shim file deleted. | ~~2026-06-30~~ | Removed ahead of schedule. | PLATARCH-REMOVE-WEB-004 ✅ |
| COMPAT-WEB-005 | `apps/web/src/hooks/useApiShared.ts` | Constant alias shim | web-platform | Backward-compatible stale-time aliases preserved for legacy hook imports; canonical keys are the non-legacy names in the same module. | 2026-07-15 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-005 |
| COMPAT-WEB-006 | `apps/web/src/hooks/useBenchmarks.ts` | Type export shim | web-platform | Backward-compatible type re-export to avoid import churn; canonical types are in `apps/web/src/schemas/benchmark.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-006 |
| COMPAT-WEB-007 | `apps/web/src/hooks/useFormulas.ts` | Type export shim | web-platform | Backward-compatible type re-export for formula consumers; canonical types are in `apps/web/src/schemas/formula.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-007 |
| COMPAT-WEB-008 | `apps/web/src/hooks/useVariables.ts` | Type export shim | web-platform | Backward-compatible type re-export for variable consumers; canonical types are in `apps/web/src/schemas/variable.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-008 |
| COMPAT-WEB-009 | `apps/web/src/hooks/useValuePacks.ts` | Type export shim | web-platform | Backward-compatible schema type re-export; canonical types are in `apps/web/src/schemas/valuePack.ts`. | 2026-06-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-009 |
| COMPAT-WEB-010 | `apps/web/src/components/ui/fabric/LoadingSkeleton.tsx` | UI component compatibility shim | web-platform | Deprecated fabric wrapper kept for callers still using legacy skeleton component. Canonical replacements: `@/components/ui/skeleton` and `@/components/ui/SkeletonViews`. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-010 |
| COMPAT-WEB-011 | `apps/web/src/components/blocks/SectionCard.tsx` | Prop alias shim | web-platform | `subtitle` alias retained for backward compatibility while callers migrate to canonical `description` prop. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-011 |
| COMPAT-WEB-012 | `apps/web/src/components/AppShell.tsx` | Controlled/uncontrolled state shim | web-platform | Internal fallback state remains for older callers not yet passing controlled props. Canonical usage is controlled props from workspace shells. | 2026-08-15 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-012 |
| COMPAT-WEB-013 | `apps/web/src/components/workspace/RightRail.tsx` | AG-UI prop compatibility shim | web-platform | Backward-compatible RightRail prop contract maintained during `useAgentEvents` rollout. | 2026-08-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-013 |
| COMPAT-WEB-014 | `apps/web/src/config/auth.ts` | Provider option compatibility shim | web-platform | Legacy Microsoft provider key retained for existing tenant configs. Canonical provider list is managed via current auth provider config. | 2026-09-30 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-014 |
| COMPAT-WEB-015 | `apps/web/src/schemas/auth.ts` | Role parsing compatibility shim | web-platform | Parser accepts frontend tier aliases in addition to canonical backend roles to prevent auth payload drift during migration. | 2026-07-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-015 |
| COMPAT-WEB-016 | `apps/web/src/stores/userTierStore.ts` | Legacy route alias shim | web-platform | Legacy route redirects retained while route canonicalization completes. | 2026-08-31 | Platform Architecture approved 2026-05-18; reviewed 2026-05-18. | PLATARCH-REMOVE-WEB-016 |

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

- **Canonical owner/path:** `value_fabric/layer3` (Layer 3 runtime implementation).
- **Compatibility owner/path:** `services/layer3-knowledge/src` for designated mirrored directories only.
- **Allowed non-mirrored exceptions in service tree:** `api/`, `agents/`, `cache/`, `docs/`, `metrics/`, and top-level `config.py` stay service-local and are not required to exist under `value_fabric/layer3`.
- **Guardrail:** mirrored paths in `services/layer3-knowledge/src` must remain thin `from value_fabric.layer3... import *` shims; implementation logic must not diverge from canonical runtime modules.



## Frontend Shim Inventory (apps/web/src)

| Shim path | Canonical replacement path | Current callers (2026-05-18 sweep) | Risk tier | Target removal milestone |
|---|---|---|---|---|
| `apps/web/src/services/sessionService.ts` (`getSessionSnapshot`/`persistSession` family) | `SessionMeta` APIs in `apps/web/src/services/sessionService.ts` | **Removed on 2026-05-18** (no runtime callers) | Low | Completed in Sprint 6 (2026-05-18) |
| `apps/web/src/hooks/useAgentStream.ts` | `apps/web/src/agui/useAgentEvents.ts` | `apps/web/src/agui/useAgentEvents.ts` (default actions helper) | Medium | Sprint 7 AG-UI convergence |
| `apps/web/src/navigation/navHelpers.ts` | `apps/web/src/navigation/navigationService.ts` | `GlobalLayout`, `MobileNavigation`, `MobilePersistentSidebar`, `TieredNav` | Medium | Sprint 7 navigation unification |
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
