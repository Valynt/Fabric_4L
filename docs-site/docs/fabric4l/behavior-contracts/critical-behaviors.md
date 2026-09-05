---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Critical Behaviors

A behavior is **critical** when its failure would compromise tenant isolation, authentication, authorization, data privacy, billing correctness, production availability, security posture, or compliance evidence.

> **No critical behavior exists unless it is tested.**

This page defines what constitutes a critical behavior, provides layer-by-layer examples from the ValuePact codebase, and describes the behavior-debt process for discovering and closing coverage gaps.

## What makes a behavior critical

Use the following criteria to classify a behavior as critical. If any criterion applies, the behavior must have an allowed test, a denied test, and an explicit failure mode.

| Criterion | Example failure |
|---|---|
| **Tenant isolation** | Tenant A reads or mutates Tenant B data |
| **Authentication** | Unauthenticated request reaches a protected endpoint |
| **Authorization** | A user without the `admin` role accesses admin-only APIs |
| **Data privacy** | PII is returned without encryption or masking |
| **Billing correctness** | Usage is recorded against the wrong tenant or plan |
| **Production availability** | A missing config check causes startup failure in production |
| **Security posture** | OWASP Top 10 category is unmitigated and untested |
| **Compliance evidence** | An audit log entry is missing or tampered with |

!!! warning "When in doubt, classify as critical"
    It is safer to over-classify and later relax than to discover a gap in production. If you are unsure whether a behavior is critical, treat it as critical and file a behavior-debt ticket.

## Critical behaviors by layer

### Layer 1: Ingestion

Layer 1 manages Playwright crawling, Celery jobs, Redis queues, and PostgreSQL state. Critical behaviors include job lifecycle enforcement, source tracking, and tenant-scoped queue access.

| Behavior | Allowed | Denied | Representative test |
|---|---|---|---|
| Tenant-scoped job enqueue | A tenant can submit an ingestion job for its own data | A tenant cannot enqueue a job targeting another tenant's source | `tests/security/test_tenant_isolation.py` |
| SSRF protection | Crawler fetches allowed domains only | Crawler is blocked from internal metadata endpoints | `tests/security/test_l1_ssrf_blocklist.py` |
| Job state transitions | Job moves from `pending` → `running` → `completed` | Invalid transitions (e.g., `completed` → `pending`) are rejected | Service-layer unit tests |
| Provenance metadata | Every ingest payload carries source and lineage | Missing provenance causes validation failure | `tests/contract/test_l3_provenance_audit_contract.py` (downstream) |

### Layer 2: Extraction

Layer 2 performs ontology-guided extraction using Pydantic v2, LLM extraction, and RDF/OWL generation. Critical behaviors include schema conformance, provenance preservation, and structured entity emission.

| Behavior | Allowed | Denied | Representative test |
|---|---|---|---|
| Ontology-guided extraction | Valid input produces structured entities matching the ontology | Unstructured blobs are rejected where structured output is required | `services/layer2-extraction/tests/test_*.py` |
| SSE streaming safety | Streamed extraction events are well-formed and bounded | Malformed or infinite streams are terminated gracefully | `services/layer2-extraction/tests/test_sse_streaming_behavior.py` |
| Cross-tenant data denial | Tenant A cannot trigger extraction on Tenant B documents | Hostile cross-tenant requests fail closed with 403 | `services/layer2-extraction/tests/test_cross_tenant_hostile_behavioral.py` |
| Batch provenance | Batch ingest preserves document-level provenance | Missing provenance fields fail batch validation | `tests/contract/test_l3_provenance_audit_contract.py` |

### Layer 3: Knowledge Graph

Layer 3 manages Neo4j, GraphRAG, hybrid retrieval, pgvector, and subgraph APIs. Critical behaviors include graph query tenant filtering, vector index integrity, and semantic retrieval scoping.

| Behavior | Allowed | Denied | Representative test |
|---|---|---|---|
| Tenant-scoped graph queries | Tenant sees only its own nodes and edges | Cross-tenant Cypher traversal returns empty or 403 | `tests/security/test_graph_tenant_hostile_regression.py` |
| Neo4j RLS enforcement | Write operations include implicit tenant filter | Write without tenant context fails closed | `tests/security/test_neo4j_rls_write.py` |
| Vector retrieval bounds | Similarity search returns only tenant-owned embeddings | Cross-tenant similarity results are excluded | `tests/security/test_layer3_similarity_roi_tenant_isolation.py` |
| Formula alias parity | Public formula aliases resolve to canonical internal names | Alias drift is caught at contract time | `tests/contract/test_l3_formula_alias_contract.py` |

### Layer 4: Agents

Layer 4 runs LangGraph workflows, ROI calculation, business case generation, and checkpoint/resume logic. Critical behaviors include output schema validation, provider-agnostic orchestration, and stream tenant isolation.

| Behavior | Allowed | Denied | Representative test |
|---|---|---|---|
| Structured agent output | Agent emits JSON matching the versioned output schema | Schema mismatch is caught and returned as structured error | `tests/contract/test_l4_workflows_contract.py` |
| Checkpoint resume | Interrupted workflow resumes from last checkpoint | Corrupted checkpoint state triggers graceful restart, not data loss | Service-layer integration tests |
| Stream tenant isolation | Streaming agent responses include tenant-scoped tool calls | Cross-tenant tool invocation is blocked mid-stream | `tests/security/test_layer4_stream_tenant_adversarial_contract.py` |
| Provider agnosticism | Core orchestration works with any configured LLM adapter | OpenAI-specific response structures do not leak into core logic | `tests/arch/test_canonical_module_sentinels.py` |

### Layer 5: Ground Truth

Layer 5 validates TruthObjects, maturity ladders, and evidence-backed claims. Critical behaviors include immutable evidence links, auditable maturity scoring, and mutation protection.

| Behavior | Allowed | Denied | Representative test |
|---|---|---|---|
| TruthObject validation | Valid claim with evidence passes validation | Claim without evidence is rejected | `tests/contract/test_l4_l5_concrete_response_contracts.py` |
| Audit mutation protection | Audit log entries are append-only | Any mutation or deletion of audit events is rejected | `tests/security/test_layer5_audit_mutation_protection.py` |
| Maturity ladder scoring | Maturity score is computed deterministically from evidence | Score manipulation without evidence fails validation | Service-layer unit tests |
| Governance control bypass | Authorized governance action succeeds | Unauthorized bypass attempt is logged and rejected | `tests/security/test_layer5_policy_enforcement_bypass.py` |

### Layer 6: Benchmarks

Layer 6 manages peer comparison, statistical validation, datasets, and benchmark policies. Critical behaviors include dataset lineage integrity, tenant-scoped benchmark usage, and statistical correctness.

| Behavior | Allowed | Denied | Representative test |
|---|---|---|---|
| Tenant-scoped benchmarks | Tenant can run benchmarks against its own data | Tenant cannot access another tenant's benchmark runs | `tests/security/test_benchmarks_cross_tenant_isolation.py` |
| Dataset lineage | Every benchmark dataset carries lineage metadata | Unsourced datasets are rejected from comparison | Service-layer contract tests |
| Statistical validation | Peer comparison uses approved statistical methods | Invalid or biased comparisons are flagged | Service-layer unit tests |

### Cross-layer and platform-wide

Some critical behaviors span all layers and are enforced by dedicated test suites.

| Behavior | Allowed | Denied | Representative test |
|---|---|---|---|
| JWT validation | Valid token grants access to scoped resources | Invalid, expired, or cross-tenant JWT is rejected | `tests/security/test_jwt_validation.py` |
| Auth bypass guardrails | Production starts with strict auth configuration | Dev bypass flags cause startup failure in production | `tests/contract/test_startup_bypass_guard_contract.py` |
| Audit log emission | Every sensitive action emits an audit event | Missing audit event triggers contract failure | `tests/audit/test_auth_events_logged.py` |
| Rate limiting | Requests within quota succeed | Requests over quota receive 429 with retry-after | `tests/security/test_rate_limit_response.py` |
| Service-to-service JWT | Internal calls carry valid tenant-scoped JWT | Missing or invalid internal JWT fails closed | `tests/security/test_l1l2_service_to_service_jwt.py` |

## Identifying missing critical behavior coverage

Use the following checklist during code review, design review, or sprint planning:

1. **Does the capability have an allowed test?**
   - Can you point to a test that proves the happy path works?
   - Is the test named after the behavior, not the method? (`test_authenticated_user_can_read_own_data`, not `test_get_user_returns_200`)

2. **Does the capability have a denied test?**
   - Can you point to a test that proves the hostile path is blocked?
   - Does the denied test assert the exact failure mode (status code, exception, safe default)?

3. **Is the failure mode explicit and tested?**
   - When something goes wrong, is the error code stable and documented?
   - Does the test verify the response does not leak secrets, stack traces, or cross-tenant data?

4. **Is there a gate that enforces it on every PR?**
   - Does a pytest marker exist?
   - Is the marker included in `make check-behavior-contract` or `make production-readiness-gate`?

5. **Is the behavior covered across layers?**
   - If the behavior spans layers, is there a cross-layer contract test in `tests/contract/` or `tests/backend_integrated/`?

If any answer is "no," the behavior has a coverage gap.

## Behavior-debt ticket process

When a critical behavior is discovered to be untested, follow the behavior-debt process. Do not merge additional logic on top of the untested behavior until the contract is encoded.

### Steps

1. **File a behavior-debt ticket**
   - Use the template: `BEHAVIOR-DEBT-<LAYER>-<NNN>`
   - Link to the code location, the missing allowed/denied test, and the expected failure mode.

2. **Add a `TODO(behavior-debt)` comment**
   - Place the comment adjacent to the untested logic.
   - Include the ticket ID and a one-line description of the missing test.

   ```python
   # TODO(behavior-debt): BEHAVIOR-DEBT-L4-003
   # Missing: denied test for cross-tenant checkpoint resume.
   # Expected failure mode: 403 with structured error envelope.
   ```

3. **Prioritize in the next sprint**
   - Behavior-debt tickets are P1 for the owning team.
   - They block promotion of related features to production readiness.

4. **Do not extend untested surfaces**
   - Until the contract is encoded, do not add new features that depend on the untested behavior.
   - This prevents compound debt.

### TODO(behavior-debt) convention

| Element | Convention |
|---|---|
| Prefix | `TODO(behavior-debt):` |
| Ticket ID | `BEHAVIOR-DEBT-L{1-6}-NNN` or `BEHAVIOR-DEBT-PLATFORM-NNN` |
| Description | One line: what test is missing and what it must prove |
| Expected failure mode | Optional second line: the explicit error code or safe default |

!!! tip "Make TODOs discoverable"
    Use `grep -r "TODO(behavior-debt)" services/ tests/ apps/web/src/` in CI or locally to produce a debt dashboard. The `make check-behavior-contract` gate can optionally fail if new `TODO(behavior-debt)` comments are added without a corresponding waiver.

## Examples of good and bad test names

Tests should be named after the behavior they prove, not the method they call.

| Good (behavior-named) | Bad (method-named) |
|---|---|
| `test_authenticated_user_can_read_own_tenant_data` | `test_get_user_returns_200` |
| `test_cross_tenant_read_fails_closed_with_403` | `test_get_user_other_tenant` |
| `test_unauthenticated_request_is_rejected_with_401` | `test_auth_fail` |
| `test_agent_output_schema_mismatch_is_caught` | `test_run_agent` |

## Related documentation

- [Test Strategy](test-strategy.md) — Marker definitions and execution commands
- [Gate Registry](gate-registry.md) — Readiness ladder and waiver policy
- `docs/governance/behavior-first-testing.md` — Canonical governance statement
- `docs/testing/` — Canonical testing governance and behavior-readiness guidance
