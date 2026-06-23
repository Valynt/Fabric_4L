# Layer 2 Provenance Tracker Persistence Design

> **Status:** design only
> **Audit item:** S6-8
> **Scope:** `services/layer2-extraction/`
> **Last updated:** 2026-06-05

## Purpose

Layer 2 already builds extraction provenance in `layer2_extraction.output.provenance` and validates the in-memory tracker through `services/layer2-extraction/tests/test_provenance.py`. The next production step is durable, tenant-scoped provenance persistence so extraction lineage can survive process restarts and support replay, audit, and downstream trust scoring.

This document defines the persistence design and test plan only. It does not add runtime persistence, migrations, or public API routes.

## Persistence Boundary

Layer 2 remains responsible for extraction provenance through these records:

| Record | Description |
|---|---|
| Provenance activity | One extraction run, keyed by `activity_id`, `tenant_id`, optional `job_id`, source document identity, model/prompt metadata, started/completed timestamps, and status |
| Provenance step | Ordered extraction stage entries such as chunking, entity extraction, relationship extraction, alignment, validation, and RDF serialization |
| Provenance artifact link | Entity IDs, relationship IDs, output paths, prompt template versions, and source hashes produced by an activity |

Layer 2 must not persist Layer 3 graph traversal state, Layer 4 agent reasoning, Layer 5 truth validation state, or Layer 2.5 signal lifecycle state. Those remain owned by their respective layers.

## Proposed Schema

Use PostgreSQL with additive Alembic migrations under `services/layer2-extraction/migrations/versions/`.

Proposed tables:

| Table | Key Fields | Notes |
|---|---|---|
| `extraction_provenance_activities` | `id`, `tenant_id`, `job_id`, `source_id`, `source_hash`, `status`, `started_at`, `completed_at`, `prompt_template_version`, `model_name`, `metadata_json` | `tenant_id` is required and part of all lookup predicates |
| `extraction_provenance_steps` | `id`, `tenant_id`, `activity_id`, `step_name`, `started_at`, `completed_at`, `input_count`, `output_count`, `llm_calls`, `status`, `metadata_json` | Foreign key includes activity identity; queries also filter by `tenant_id` |
| `extraction_provenance_artifacts` | `id`, `tenant_id`, `activity_id`, `artifact_type`, `artifact_id`, `artifact_uri`, `source_span_json`, `confidence`, `metadata_json` | Stores entity/relationship/output lineage without duplicating full payloads |

Indexes:

- `(tenant_id, id)` on every table.
- `(tenant_id, job_id)` on activities.
- `(tenant_id, activity_id, step_name)` on steps.
- `(tenant_id, artifact_type, artifact_id)` on artifacts.

RLS:

- Enable row-level security on all three tables.
- Policy predicate: `tenant_id = current_setting('app.tenant_id', true)`.
- Repository sessions must set tenant context before any query.

## Write Flow

1. Extraction starts with an authenticated or worker-propagated `tenant_id`.
2. The existing provenance tracker creates an activity in memory.
3. The future repository writes the activity row before the first extraction step.
4. Each completed step appends a step row and updates activity status metadata.
5. Entity, relationship, and output-path lineage append artifact-link rows.
6. On failure, the activity is marked failed with non-sensitive error metadata.

Writes must fail closed when `tenant_id` is missing or blank. Request body, query, and header tenant values must not override authenticated context or trusted Celery payload context.

## Read And Replay Shape

Future internal reads should support:

- `get_activity(tenant_id, activity_id)` returns one activity with ordered steps and artifacts.
- `list_activities_for_job(tenant_id, job_id)` returns all provenance activity summaries for a job.
- `get_artifact_lineage(tenant_id, artifact_type, artifact_id)` returns the producing activity and source spans.
- `replay_activity(tenant_id, activity_id)` returns deterministic replay inputs and prompt/model metadata, but does not re-run LLM calls unless a separate replay workflow requests it.

No public API route is approved by this design. If a route is later added, it must be reflected in OpenAPI, frontend types, contract tests, and docs.

## Migration Plan

1. Add additive Alembic migration with the three tables, indexes, and RLS policies.
2. Add a `ProvenanceRepository` with async create/update/list/read methods.
3. Wire repository calls behind a configuration flag defaulting to enabled in production and safe no-op only in explicit test mode.
4. Backfill only if durable provenance records already exist elsewhere; otherwise start from new extraction runs.
5. Add retention policy configuration after the first production evidence review.

Rollback for the initial migration should drop only the newly added tables and policies. No existing Layer 2 extraction state should be modified.

## Test Plan

Required before implementation can be marked complete:

- Unit tests for repository create/update/read behavior with required `tenant_id`.
- Hostile tenant tests proving Tenant A cannot read Tenant B activities, steps, or artifacts.
- Missing-context tests proving repository calls fail closed before SQL executes.
- Migration tests validating one Alembic head and reversible additive migration behavior.
- Existing provenance tests in `services/layer2-extraction/tests/test_provenance.py` must continue to pass.
- Contract tests only if a public API route is introduced.

Suggested commands:

```bash
python -m pytest services/layer2-extraction/tests/test_provenance.py -v --tb=short
python -m pytest services/layer2-extraction/tests -k "provenance or tenant" -v --tb=short
python scripts/ci/check_migration_safety.py --strict
```

## Acceptance Criteria

S6-8 is complete when this design is reviewed and linked from the remediation register. Full persistence implementation remains a separate scoped item and must not be inferred from this design-only closure.
