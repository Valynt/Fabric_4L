# L2 Component — layer5-ground-truth

## Purpose

Ground-truth, value-claims, and governance layer (`services/layer5-ground-truth/`). Owns
validated and disputed truth state, source references, corroboration policy, and publication
readiness. Evidence requirements are explicit mandatory policy, deterministic and
configuration-controlled (GAP-10); semantic search results are candidates, not truth, until the
configured validation policy promotes them.

## Owned journey stages / behaviors

- BEH-02 hypothesis-capture — assumption governance for validation/promotion
  (`.../api/assumption_governance_routes.py`)
- BEH-05 evidence-and-cost-binding — value claims and evidence state
  (`.../api/value_claim_routes.py`)
- BEH-08 approval-and-publication — governance gates and publication readiness
  (`.../api/governance_router.py`)
- Cross-cutting — model registry (`.../api/model_registry_routes.py`), academy
  (`.../api/academy_router.py`); review queue feeds `apps/web` `ReviewQueuePage.tsx`

## Key verified paths

- `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py` — API entry
- api routers: `router.py`, `governance_router.py`, `value_claim_routes.py`,
  `assumption_governance_routes.py`, `model_registry_routes.py`, `academy_router.py`
  (+ matching `*_schemas.py`, `auth.py`)
- Package subdirs: `adapters/`, `integration/`, `jobs/`, `migrations/`, `models/`,
  `observability/`, `repositories/`, `services/`; root `cache.py`, `config.py`, `database.py`,
  `runtime_mode.py`, `shared_bootstrap.py`
- `services/layer5-ground-truth/src/metrics/`
- Root: `README.md`, `AGENTS.md`, `alembic.ini`, `pytest.ini`

## Dependencies

- Consumed by `services/layer4-agents` (truth gates in workflows) and `services/api`.
- Contracts: `contracts/openapi/layer5-ground-truth/`,
  `contracts/jsonschema/claim-types.v1.json`.
- Evidence and provenance records must satisfy R-8 (claim → calculation → formula → inputs →
  driver → signal/evidence → original source).

## Primary gates

- **AG-05** tenant-isolation-and-behavior — tenant/account scope on truth and evidence records.
- **AG-02** code-quality-and-tests — deterministic golden datasets, scoring calibration,
  negative tests for evidence policy.
- **AG-04** security-gates — governance and claim routes authorization.
