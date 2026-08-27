# Task 1: Validate debt assessment and execute safest first remediation slice

Treat the Brooks-Lint report as an assessment, not authorization for a repository-wide refactor. Validate every finding against the current repository and produce a dependency-aware remediation order. Then implement only the safest, narrowest, independently mergeable remediation slice, preferring Layer 1 model consolidation if semantic equivalence is proven.

Required validation for each finding: exact files/modules, canonical implementation, callers/importers, runtime/deployment reachability, tests, CI/workflow references, documentation/ADR references, intentionality, migration work, and blockers. Explicitly classify each as CONFIRMED, PARTIAL, STALE, INTENTIONAL, or FALSE POSITIVE.

Constraints: work only in this isolated worktree based on current main; do not delete compatibility code without proving zero callers; preserve tenant isolation, authorization, provenance, API contracts, fail-closed behavior, tests, gates, and generated-code ownership; do not perform broad formatting or unrelated cleanup; keep the implementation to one clear architectural purpose; add regression protection against duplicate definitions returning; run focused tests, structural/import checks, and affected tenancy/contract checks.

The likely first slice is:
- compare `services/layer1-ingestion/src/layer1_ingestion/shared/models.py` and `services/layer1-ingestion/src/shared/models.py`;
- prove whether they define equivalent runtime entities and whether base-class differences matter;
- if equivalent, select the canonical implementation, migrate direct consumers, retain only a compatibility re-export if callers remain, and add a focused regression guard;
- if equivalence or reachability is not sufficiently proven, do not edit production code; instead report the blocker and provide the validated table and remediation sequence.

Final report must include: validated findings table; dependency-aware remediation sequence; exact files changed; tests and CI validation; remaining blockers/dependencies; updated health assessment; and explicit non-goals.
