# Layer 3 Integrity Audit Implementation Plan

**Goal:** Make Layer 3 batch ingestion outcomes accurate and fail-closed while producing a comprehensive audit and validation record.

**Architecture:** Preserve the RDF orchestrator, batch writers, and centralized audited mutation gateway. Consume Neo4j result records at the gateway and propagate storage failures through writers.

**Tech Stack:** Python 3.11, Neo4j async driver, pytest, pytest-asyncio, Ruff, mypy.

## Global Constraints

- Modify only Layer 3-owned runtime, tests, and documentation.
- Preserve tenant-scoped `MERGE` keys and public Layer 2/Layer 4 contracts.
- Do not claim live Neo4j validation from mocked tests.

---

### Task 1: Establish the audit baseline

**Files:**
- Inspect: `services/layer3-knowledge/src/`
- Inspect: `contracts/openapi/layer3-knowledge.json`
- Inspect: `contracts/jsonschema/layer3-entity-resolution-contract.json`

- [ ] Run the canonical Layer 3 lint and test entrypoints and record environment limitations.
- [ ] Inventory mutation, constraint, index, retrieval, and tenant-scoping paths.
- [ ] Select only defects supported by source and test evidence.

### Task 2: Prove accurate batch outcomes and fail-closed errors

**Files:**
- Modify: `services/layer3-knowledge/tests/ingestion/neo4j/test_writers.py`
- Modify: `services/layer3-knowledge/tests/test_audited_graph_mutation.py`

**Interfaces:**
- Consumes: `EntityBatchWriter.write`, `RelationshipBatchWriter.write`, and `AuditedGraphMutation.write_*_batch`.
- Produces: regression assertions for Neo4j-returned counts and propagated mutation exceptions.

- [ ] Add a gateway fixture that returns a count smaller than its input and one that raises a storage error.
- [ ] Assert writers return the gateway count.
- [ ] Assert writers re-raise storage failures.
- [ ] Add mutation-result fixtures whose `single()` record contains `merged`.
- [ ] Run the focused tests and confirm they fail for the intended reasons.

### Task 3: Implement the minimal ingestion fix

**Files:**
- Modify: `services/layer3-knowledge/src/db/audited_mutation.py`
- Modify: `services/layer3-knowledge/src/ingestion/neo4j/writers.py`

**Interfaces:**
- Produces: unchanged `dict[str, Any]` mutation responses with accurate `count` values; writer exceptions now reach callers.

- [ ] Consume the result of each batch mutation query and read `merged`, defaulting safely to zero when no record exists.
- [ ] Retain failure metrics and logs, then re-raise writer exceptions.
- [ ] Run focused tests to confirm green.

### Task 4: Audit report and validation

**Files:**
- Create: `services/layer3-knowledge/docs/LAYER3_AUDIT_2026-08-16.md`

- [ ] Document architecture, severity-ranked findings, exact components, evidence, changes, backlog, deferred cross-layer findings, and residual risks.
- [ ] Run formatting, lint, typing, unit, tenant, schema, contract, and security checks.
- [ ] Attempt live Neo4j integration and query-plan checks; clearly record any environment limitation.
- [ ] Review the diff for scope and secrets, commit with a conventional message and co-author trailer, and create the required pull request.
