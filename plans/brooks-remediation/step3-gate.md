# Step 3 — L3 Deprecation-Alias Removal Gate (Gate Verification Only)

**Date:** 2026-08-27
**Owner:** Brooks-Lint remediation PR (`valyntxyz-reimagined-telegram`)
**Scope:** Gate verification + stale-consumer audit only. **NO removal merge performed** in this PR — removal is owned by the `docs/superpowers/plans/2026-08-26-layer3-facade-migration.md` plan PR.

> Decision #2 in `plans/brooks-remediation/plan.md` assigns gate + audit to this
> PR and the actual alias removal to the existing L3 facade-migration PR. This
> document records the gate verdict and the audit evidence for that handoff.

## Verdict: **PASS** (gate is green; removal may proceed when the owning PR lands)

## Evidence — Live Compat Metrics Counters

Checked with a fresh interpreter using the canonical `compat_metrics` snapshot API
(`src/services/compat_metrics.py`):

```
snapshot: {'route_hits': {}, 'legacy_field_hits': {}}
ready_for_removal: True
thresholds: {'max_legacy_route_hits_7d': 0, 'max_legacy_field_hits_7d': 0}
```

- `route_hits` and `legacy_field_hits` are empty → both totals are **0**, at or
  below the acceptance threshold of `0`.
- `deprecation_ready_for_removal(snapshot)` returns **True**.

The gates live in `src/services/compat_policy.py`:
- `GraphNodeAliasMap = {"label": "name", "type": "entity_type", "confidence": "confidence_score"}`
- `GraphEdgeAliasMap = {"relationship_type": "type"}`
- `CompatibilityPolicy.ready_for_removal()` requires route and field totals ≤ 0.

Note: counters are in-process (reset on service restart) — a fresh-process zero
snapshot is necessary but **not sufficient** on its own. See "Residual risk"
below for the production-trend requirement.

## Evidence — Live Service Deprecation Phase

- Default phase is `warning_only` (`DEFAULT_COMPAT_DEPRECATION_PHASE`); aliases
  remain in responses via `include_graph_field_aliases()` unless phase is
  `removed`. The removal PR must flip phase to `removed` **and** cut the
  `v2.5` `GRAPH_FIELD_ALIAS_REMOVAL_VERSION` as part of its merge.

## Evidence — Stale-Consumer Audit (reads of removed aliases)

### Backend contract tests (owned by removal PR, expected to change there)
- `tests/contract/test_l3_graph_contract.py` asserts deprecated aliases are
  **present** in serialized output (L264–265 `label`, L271–273 `confidence`,
  L305–325 `relationship_type`) and must be updated by the removal PR.
- `tests/contract/test_layer3_graph_deprecation_contract.py` asserts the
  deprecation-phase behavior, including `removed` phase dropping the aliases
  (L57–60) — this is the executable spec for the removal.
- `tests/contract/test_l3_graph_contract.py` FIXED canonical reads already use
  `name`, `entity_type`, `confidence_score` (L37, L60, L146–150).

### Frontend consumers (outside `generated/`)
- `apps/web/src/features/graph/domain/graph.mapper.ts` reads deprecated aliases
  **as fallbacks only**, guarded by type-checks:
  - L50–51: `if ('label' in dto && typeof dto.label === 'string' ...)` →
    preferred canonical `name`; `label` is the fallback.
  - L71–72: `'confidence' in dto` fallback for `confidence_score`.
  - L84–85: `'relationship_type' in dto` fallback for `type`.
- Other frontend `.label` / `.confidence` matches (`QuizQuestion.tsx`, tabs,
  `types/api.ts`, etc.) are unrelated UI-local controls / use-case confidence,
  not L3 graph aliases.
- This mapper is a **canonical-first reader**: it will keep working after removal,
  so no frontend change is strictly required at removal time, but it should be
  simplified to drop the fallback branches in the same PR (grep audit finding).

### OpenAPI contract
- `contracts/openapi/layer3-knowledge.json` currently still documents the alias
  fields; the removal PR must update it, regenerate TS types
  (`apps/web/src/api/generated/l3/index.ts`), and re-run `pnpm run check:api-types`
  in that order (contract → backend → generated TS → frontend mapper).

## Commit sequencing (for removal PR, not performed here)

Per plan decision — CI must stay green at each commit:
1. Contract (OpenAPI + JSON Schema) → 2. Backend phase flip to `removed` →
3. Regenerate TS types → 4. Frontend mapper fallback removal → 5. Delete
   `compat_shims` and the deprecation tests that assert alias presence.

## Residual risk

- Fresh-process counter zero **does not prove** production 7-day counter trend.
  The owner must confirm live `layer3_deprecated_route_hits_total` /
  `layer3_legacy_field_usage_total` Prometheus counters trend to zero over the
  window before merging removal.
- Removal is a breaking contract change (`relationship_type`, `.label`,
  `.confidence`, `.type` drops). The `test_layer3_graph_deprecation_contract.py`
  suite is the safety net: removal that forgets any alias will fail it.

## Recommendation

Merge this PR as-is (gate PASS recorded, no removal here). Hand this document to
the `2026-08-26-layer3-facade-migration.md` PR as the gate artifact.