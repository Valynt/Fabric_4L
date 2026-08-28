# 08 — Definition of Done

Source: Master Product Intent §8 (S1). 19 items across four disciplines.

Release rule: "A feature is not done when the page renders or the route returns 200. It is done when the user outcome, domain transition, cross-service contract, evidence, authorization, accessibility, observability, and candidate-build proof all agree."

## Product and design

1. Product confirms the intended user outcome, entry condition, lifecycle transition, exit gate, and success measure.
2. Design covers happy, empty, loading, generating, partial, degraded, stale, conflict, error, denied, expired, review, approval, and recovery states.
3. Terminology, action labels, routes, account context, scenario identity, and version identity are consistent across Intelligence, Value Studio, Calculator, Narrative, Value Case, Deliverables, and Realization.
4. Accessibility and responsive behavior are specified and verified (keyboard, focus, status announcements, chart alternatives, non-color semantics).

## Engineering and data

1. One canonical server-side source of truth and one versioned contract exist for the story's domain artifact and actions.
2. Tenant, account, case, model, artifact, and version scope are derived and enforced at every relevant boundary, key, query, cache, and object path.
3. Writes are idempotent, concurrent updates guarded, failures preserve valid work, recovery is tested.
4. Deterministic calculations, formula validation, evidence policy, provenance, source classification, and fallback disclosure are verified.
5. Migrations, indexes, tenant-inclusive constraints, data retention, and rollback behavior defined for new persisted state.

## Quality and certification

1. Unit tests cover calculations, validation, state transitions, and failure branches without weakening thresholds.
2. Contract tests prove frontend types and service request/response schemas align.
3. Integration tests use real persistence and service boundaries for the affected slice (timeout, retry, duplicate, stale, degraded behavior).
4. Hostile-tenancy tests cover missing scope, mismatched scope, reused IDs, same-ID collisions, parent-child mismatches, cache keys, graph queries, and storage paths.
5. Browser tests exercise canonical tenant-scoped routes, keyboard behavior, permission states, review gates, recovery states.
6. A fresh-data, candidate-SHA-bound journey proves account creation through approved export with real services and deterministic assertions, without mocked core HTTP responses or seeded value outputs.

## Operations and evidence

1. Logs, metrics, traces, workflow state, audit events, execution tier, fallback reason, data classification, and customer-facing eligibility are correlated and testable.
2. Release evidence identifies commit SHA, environment, image digests, migrations, configuration, test results, trace IDs, artifacts, and approval status.
3. Runbooks cover degraded providers, stuck jobs, version conflicts, failed exports, authorization incidents, data repair, rollback, and recovery.
4. The story is included in the authoritative release gate and cannot be bypassed by a silent fallback, skipped job, or stale artifact.
