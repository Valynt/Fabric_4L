---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Temporal security audit - superseded by fixes
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Data Intelligence Layer — Security Audit Report

**Audit Date:** 2026-04-26
**Auditor Posture:** Cold-start, zero prior context
**Scope:** All DIL files across L3 (layer3-knowledge) and L4 (layer4-agents) — 9 services, 9 route modules
**Methodology:** Manual code review against OWASP Top 10, CWE/SANS 25, and multi-tenant SaaS security baselines

---

## Executive Summary

The Data Intelligence Layer introduces **~50 new API endpoints** across 9 route modules with **zero authentication enforcement** on any of them. Tenant isolation relies entirely on a spoofable HTTP header (`X-Tenant-ID`) with no server-side verification. The enrichment pipeline makes outbound HTTP requests to URLs derived from user-controlled database fields, creating an SSRF vector. One service constructs Cypher `SET` clauses from user-supplied dictionary keys, enabling property injection. Multiple services accept caller-supplied data payloads that are persisted without server-side re-validation.

**Violation Counts by Severity:**

| Severity | Count |
|----------|-------|
| Critical | 4     |
| High     | 7     |
| Medium   | 6     |
| Low      | 4     |
| **Total** | **21** |

---

## Violation Catalog

### V-001: No Authentication on Any DIL Endpoint

```json
{
  "severity": "critical",
  "category": "auth",
  "location": "All 9 route modules (see list below)",
  "finding": "None of the ~50 new endpoints declare any authentication dependency (e.g., Depends(require_authenticated), OAuth2 bearer, API key). Every endpoint is publicly accessible to any caller who can reach the network.",
  "why_builder_missed_it": "Completion pressure to deliver 3 phases of functionality. Auth was likely assumed to be handled by an upstream middleware or gateway that does not yet exist in the route registration path for these modules.",
  "probe": "Ask the builder: Which middleware or dependency enforces authentication before these route handlers execute? Show me the code path from incoming request to auth verification for POST /api/v1/narratives/generate."
}
```

**Affected files (every route module):**
- `layer3-knowledge/src/api/routes/products.py` — all 11 endpoints
- `layer3-knowledge/src/api/routes/evidence.py` — all 9 endpoints
- `layer3-knowledge/src/api/routes/competitive_intel.py` — all 10 endpoints
- `layer3-knowledge/src/api/routes/roi_calculator.py` — all 8 endpoints
- `layer4-agents/src/api/routes/enrichment.py` — all 4 endpoints
- `layer4-agents/src/api/routes/value_hypotheses.py` — all 7 endpoints
- `layer4-agents/src/api/routes/narratives.py` — all 5 endpoints
- `layer4-agents/src/api/routes/intelligence.py` — all 3 endpoints

---

### V-002: Tenant Identity Spoofable via Unauthenticated Header

```json
{
  "severity": "critical",
  "category": "auth",
  "location": "layer4-agents/src/api/routes/narratives.py:74-81, intelligence.py:27-34, value_hypotheses.py:67-74, competitive_intel.py:86-93, roi_calculator.py (same pattern), evidence.py:38-48, products.py:19-30",
  "finding": "All _extract_tenant_id() helpers accept the raw X-Tenant-ID header value as the authoritative tenant identity. There is no verification that the caller is authorized to act on behalf of that tenant. Any caller can impersonate any tenant by setting the header.",
  "why_builder_missed_it": "The builder replicated the pattern from existing routes (products.py) which was already insecure. Copy-paste propagation of a flawed pattern across all 9 modules.",
  "probe": "Ask the builder: How is the X-Tenant-ID header value validated against the authenticated user's authorized tenants? What prevents Tenant-A from setting X-Tenant-ID: Tenant-B?"
}
```

**Two distinct variants exist:**

| Variant | Files | Pattern |
|---------|-------|---------|
| L3 pattern | products.py, evidence.py | `Header(None, alias='X-Tenant-ID')` via FastAPI `Depends` |
| L4 pattern | narratives.py, intelligence.py, value_hypotheses.py, competitive_intel.py | `request.headers.get('X-Tenant-ID', '')` direct access |

Both are equally spoofable. The L3 variant also falls back to `request.state.context.tenant_id`, which is populated by middleware — but that middleware's auth enforcement is not visible in the DIL code and may not exist.

---

### V-003: IDOR — Enrichment Endpoint Loads Account Without Tenant Scoping

```json
{
  "severity": "critical",
  "category": "auth",
  "location": "layer4-agents/src/api/routes/enrichment.py:64-97 (enrich_account), enrichment.py:140-165 (get_account_enrichment), layer4-agents/src/services/enrichment_orchestrator.py:167",
  "finding": "POST /enrichment/{account_id} and GET /enrichment/{account_id} load accounts solely by UUID via db.get(Account, account_id) with NO tenant_id filter. Any caller who knows or guesses an account UUID can enrich or read enrichment data for any account in any tenant. The enrichment orchestrator's enrich_account() method (line 167) also loads by UUID only.",
  "why_builder_missed_it": "The builder focused on making the enrichment pipeline functional. The Account model uses UUID primary keys, and SQLAlchemy's db.get() naturally loads by PK only. Adding a tenant filter would have required a query instead of a simple get().",
  "probe": "Ask the builder: If I call POST /enrichment/{uuid-of-competitor-tenant-account}, what prevents me from enriching and reading another tenant's account data? Show me the tenant ownership check."
}
```

---

### V-004: IDOR — Batch Enrichment Accepts Arbitrary tenant_id in Request Body

```json
{
  "severity": "critical",
  "category": "auth",
  "location": "layer4-agents/src/api/routes/enrichment.py:44-48 (BatchEnrichRequest model), enrichment.py:100-119 (enrich_batch endpoint)",
  "finding": "POST /enrichment/batch accepts tenant_id as a field in the JSON request body (BatchEnrichRequest.tenant_id). There is no comparison between this caller-supplied tenant_id and any authenticated identity. A caller can trigger batch enrichment for any tenant's accounts.",
  "why_builder_missed_it": "The enrichment route module uses a different pattern from the other routes — it takes tenant_id in the body instead of a header. This inconsistency suggests it was built quickly without aligning to the (already insecure) header pattern.",
  "probe": "Ask the builder: Why does the batch endpoint accept tenant_id in the request body rather than extracting it from the authenticated context? What stops a caller from enriching Tenant-B's accounts?"
}
```

---

### V-005: Server-Side Request Forgery (SSRF) via Web Crawl Enrichment

```json
{
  "severity": "high",
  "category": "injection",
  "location": "layer4-agents/src/services/enrichment_orchestrator.py:436-489 (_enrich_from_web_crawl)",
  "finding": "The web crawl enrichment handler constructs a URL from account.website or account.domain (line 442) and makes an outbound HTTP GET request with follow_redirects=True (line 453). These fields are stored in the database and can be set by any user who creates/updates accounts. There is no URL validation, no allowlist, no blocklist for internal IPs (127.0.0.1, 169.254.169.254, 10.x, etc.), and no restriction on protocol (http:// is accepted). An attacker who controls an account record can force the server to make requests to internal services, cloud metadata endpoints, or arbitrary external hosts.",
  "why_builder_missed_it": "The builder's goal was tech stack detection, which inherently requires fetching external URLs. SSRF mitigation was not in scope for the feature and would have required additional infrastructure (URL validation, network-level controls).",
  "probe": "Ask the builder: What prevents an attacker from setting account.website to http://169.254.169.254/latest/meta-data/iam/security-credentials/ and triggering enrichment to exfiltrate cloud credentials?"
}
```

---

### V-006: Cypher Property Injection via Dynamic SET Clause Construction

```json
{
  "severity": "high",
  "category": "injection",
  "location": "layer3-knowledge/src/services/competitive_intel_service.py:248-256 (update_competitor method)",
  "finding": "The update_competitor method builds Cypher SET clauses by interpolating dictionary keys into f-strings: `set_parts = [f'c.{k} = ${k}' for k in safe_updates]`. While the VALUES are parameterized (safe), the KEYS come from user-supplied JSON field names via CompetitorUpdateRequest.model_dump(exclude_none=True). The Pydantic model defines specific fields, but Pydantic's model_dump() will include any field the model defines. The 'protected' set only blocks {id, tenant_id, entity_type, created_at}. A crafted key like a Neo4j-valid property name could set arbitrary node properties (e.g., 'admin_override', 'is_deleted'). More critically, if Pydantic's model is ever loosened (model_config = {'extra': 'allow'}), arbitrary property names flow directly into Cypher.",
  "why_builder_missed_it": "The builder correctly parameterized values but overlooked that dictionary keys also flow into the query string. The pattern works safely only as long as the Pydantic model strictly defines all allowed fields and never allows extras.",
  "probe": "Ask the builder: If CompetitorUpdateRequest ever adds model_config = {'extra': 'allow'} or a new field is added without updating the protected set, what happens to the Cypher query? How do you ensure key names are safe for Cypher interpolation?"
}
```

---

### V-007: Enrichment Status Endpoint Accepts Arbitrary tenant_id as Query Parameter

```json
{
  "severity": "high",
  "category": "auth",
  "location": "layer4-agents/src/api/routes/enrichment.py:122-137 (get_enrichment_status)",
  "finding": "GET /enrichment/status accepts tenant_id as a query parameter with no authentication or authorization check. Any caller can view enrichment coverage statistics (total accounts, enriched count, pending count, failure count) for any tenant.",
  "why_builder_missed_it": "The builder needed a way to pass tenant_id for the status query and chose a query parameter for simplicity. Without an auth layer, there was no authenticated identity to compare against.",
  "probe": "Ask the builder: What prevents an unauthenticated caller from enumerating tenant IDs and retrieving enrichment statistics for every tenant in the system?"
}
```

---

### V-008: Pipeline Summary Exposes Tenant-Wide Financial Data Without Account-Level Authorization

```json
{
  "severity": "high",
  "category": "auth",
  "location": "layer4-agents/src/api/routes/intelligence.py:94-107 (get_pipeline_summary), layer4-agents/src/services/intelligence_orchestrator.py:274-329",
  "finding": "GET /intelligence/pipeline-summary returns aggregated data across ALL accounts for a tenant, including per-account hypothesis counts, average confidence scores, total estimated impact (USD), and validation status. Combined with V-002 (spoofable tenant header), any caller can retrieve the full pipeline intelligence for any tenant.",
  "why_builder_missed_it": "The endpoint was designed for internal dashboard use where tenant context would be trusted. The builder assumed a gateway or middleware would enforce tenant authorization upstream.",
  "probe": "Ask the builder: This endpoint returns total_pipeline_value and per-account financial impact data. What access control ensures only authorized users within a tenant can see this aggregation?"
}
```

---

### V-009: Evidence Matching Ignores Account Context — Returns All Tenant Evidence

```json
{
  "severity": "high",
  "category": "logic",
  "location": "layer4-agents/src/services/intelligence_orchestrator.py:433-446 (_get_matched_evidence)",
  "finding": "The _get_matched_evidence method accepts account_id as a parameter but the Cypher query (lines 437-441) only filters by tenant_id — it completely ignores account_id, industry, and product context. It returns the 10 newest Evidence nodes for the entire tenant regardless of which account is being briefed. This means every account briefing gets the same 'matched' evidence, defeating the purpose of account-specific intelligence.",
  "why_builder_missed_it": "The method signature suggests account-specific matching was intended (it accepts account_id), but the implementation shortcuts to a simple tenant-wide query. This is a classic 'TODO that shipped' — the builder likely planned to add account/industry filtering but ran out of time.",
  "probe": "Ask the builder: The method signature accepts account_id but the query ignores it. Is this intentional? How does an account briefing get evidence relevant to that specific account's industry and products?"
}
```

---

### V-010: Narrative Generation Accepts and Persists Arbitrary Caller-Supplied Data

```json
{
  "severity": "high",
  "category": "logic",
  "location": "layer4-agents/src/api/routes/narratives.py:55-60 (NarrativeGenerateRequest pre-fetched fields), layer4-agents/src/services/narrative_builder_service.py:157-229 (generate_narrative)",
  "finding": "The narrative generation endpoint accepts optional pre-fetched data payloads (account_data, signals_data, hypotheses_data, competitive_data, roi_data, evidence_data) directly in the request body. These are passed through to _build_context() which trusts them completely — computing financial metrics, signal counts, and evidence summaries from the caller-supplied data. The resulting narrative is then persisted to Neo4j as a tenant-scoped Narrative node. An attacker can inject fabricated intelligence data (fake ROI numbers, fake win rates, fake evidence) that gets stored as an official narrative artifact.",
  "why_builder_missed_it": "The pre-fetched data pattern was designed for the orchestration layer to avoid redundant queries. The builder assumed only trusted internal callers would use these fields. But since the endpoint is public and unauthenticated, any external caller can supply arbitrary data.",
  "probe": "Ask the builder: If I POST to /narratives/generate with hypotheses_data containing fabricated $10M impact estimates and roi_data showing 500% ROI, that data gets rendered into a narrative and stored in Neo4j. How do you prevent data poisoning of the narrative store?"
}
```

---

### V-011: Win/Loss Record Relationship Type Constructed from User Input via f-string

```json
{
  "severity": "high",
  "category": "injection",
  "location": "layer3-knowledge/src/services/competitive_intel_service.py:392-406 (record_win_loss)",
  "finding": "The record_win_loss method constructs the Neo4j relationship type using an f-string: `rel_type = 'WON_AGAINST' if record_data.outcome == 'won' else 'LOST_TO'` then `CREATE (p)-[r:{rel_type} {{...}}]->(c)`. While the current code constrains rel_type to two values via the if/else, the route layer's validation (competitive_intel.py:266) only checks `body.outcome not in ('won', 'lost')` AFTER the Pydantic model accepts the value. The WinLossRequest model (line 75) defines outcome as `str = Field(...)` with no pattern constraint. If the route validation is ever removed or bypassed, arbitrary relationship types could be injected into the Cypher query.",
  "why_builder_missed_it": "The builder added route-level validation but the defense is fragile — it relies on a runtime check rather than a type-safe enum constraint at the model level. The service layer trusts its caller.",
  "probe": "Ask the builder: Why isn't outcome constrained to a Literal['won', 'lost'] or an Enum at the Pydantic model level? What happens if someone calls the service directly (bypassing the route) with outcome='WON_AGAINST}]->(c) CREATE (x:Malicious)'?"
}
```

---

### V-012: Bulk Import Has No Rate Limiting or Size Control on Content Fields

```json
{
  "severity": "medium",
  "category": "logic",
  "location": "layer3-knowledge/src/api/routes/evidence.py:94-97 (BulkImportRequest), layer3-knowledge/src/services/case_study_service.py:403-459 (bulk_import)",
  "finding": "The bulk import endpoint accepts up to 100 case studies per request (max_length=100), but each case study's content field has no max_length constraint in CreateCaseStudyRequest (line 65: only min_length=50). An attacker can submit 100 case studies each with multi-megabyte content fields, causing memory exhaustion and slow Neo4j writes. The bulk_import method processes sequentially with individual CREATE operations (not batched), amplifying the impact.",
  "why_builder_missed_it": "The builder added a count limit (100) but overlooked per-item size limits. The sequential processing pattern was chosen for error isolation but creates a DoS amplification vector.",
  "probe": "Ask the builder: What prevents a caller from submitting 100 case studies each with 50MB of content? What is the maximum request body size? Is there a timeout on the bulk import operation?"
}
```

---

### V-013: ROI Calculator Persists Calculations Against Arbitrary account_id

```json
{
  "severity": "medium",
  "category": "auth",
  "location": "layer3-knowledge/src/api/routes/roi_calculator.py (calculate endpoint with save=True)",
  "finding": "The POST /roi/calculate endpoint accepts an optional account_id and template_id in the request body. When save=True, the calculation is persisted to Neo4j with whatever account_id the caller provides. There is no verification that the caller owns or has access to that account. This allows attaching fabricated ROI calculations to any account.",
  "why_builder_missed_it": "The save feature was added for convenience without considering that the account_id comes from the untrusted request body rather than from a verified context.",
  "probe": "Ask the builder: If I call POST /roi/calculate with account_id set to a competitor's account UUID and save=True, the calculation gets stored against their account. How do you prevent this?"
}
```

---

### V-014: Enrichment Orchestrator Swallows Exceptions and Returns Partial Success

```json
{
  "severity": "medium",
  "category": "logic",
  "location": "layer4-agents/src/services/enrichment_orchestrator.py:191-205 (enrich_account source loop)",
  "finding": "The enrichment loop catches all exceptions per source (line 197: `except Exception as e`) and appends them to an errors list. If some sources succeed and others fail, the account is marked as ENRICHED (line 209) even though enrichment is incomplete. The caller receives a 200 OK with partial results. There is no mechanism to retry failed sources or to distinguish fully-enriched from partially-enriched accounts.",
  "why_builder_missed_it": "The builder prioritized resilience over correctness — a common trade-off when integrating multiple external services. The broad exception catch was intended to prevent one source failure from blocking others.",
  "probe": "Ask the builder: If SEC EDGAR enrichment succeeds but web crawl and news scan both fail, the account is marked 'enriched'. How does a downstream consumer know the enrichment is incomplete? Is there a retry mechanism?"
}
```

---

### V-015: HTTP Client Follows Redirects Without Limit or Validation

```json
{
  "severity": "medium",
  "category": "injection",
  "location": "layer4-agents/src/services/enrichment_orchestrator.py:132-139 (_get_http_client), line 453 (web crawl)",
  "finding": "The HTTP client is created with follow_redirects=True globally (line 138) and the web crawl handler also passes follow_redirects=True (line 453). There is no limit on redirect count and no validation of redirect targets. An attacker-controlled website can redirect the server through a chain to internal services, bypassing any URL-level checks that might be added to the initial URL.",
  "why_builder_missed_it": "follow_redirects=True is the natural choice for web crawling (many sites redirect www → non-www, HTTP → HTTPS). The security implication of redirect chains to internal targets was not considered.",
  "probe": "Ask the builder: If account.website points to an attacker-controlled server that 302-redirects to http://169.254.169.254/latest/meta-data/, does the client follow that redirect?"
}
```

---

### V-016: Narrative Status Update Has No Lifecycle Validation

```json
{
  "severity": "medium",
  "category": "logic",
  "location": "layer4-agents/src/api/routes/narratives.py:63-66 (StatusUpdateRequest), narratives.py:168-182 (update_narrative_status)",
  "finding": "The status update endpoint accepts any string as the new status (StatusUpdateRequest.status is an unconstrained str field). The NarrativeStatus enum defines valid values (draft, review, approved, delivered) but the route does not validate against it. A caller can set status to any arbitrary string (e.g., 'published', 'deleted', 'admin_approved'), corrupting the lifecycle state machine.",
  "why_builder_missed_it": "The builder defined the NarrativeStatus enum in the service but forgot to use it as a validator in the route-level Pydantic model. The description mentions valid values but doesn't enforce them.",
  "probe": "Ask the builder: StatusUpdateRequest.status is a plain str. What prevents a caller from setting status to 'admin_override' or any other arbitrary string?"
}
```

---

### V-017: Value Hypothesis Validation Endpoint Allows Unbounded Confidence Manipulation

```json
{
  "severity": "medium",
  "category": "logic",
  "location": "layer4-agents/src/api/routes/value_hypotheses.py:48-53 (ValidateHypothesisRequest), layer4-agents/src/services/value_hypothesis_engine.py (validate_hypothesis)",
  "finding": "The validate endpoint accepts confidence_adjustment as a float between -1.0 and 1.0. However, there is no validation that the resulting confidence_score stays within [0, 1] after the adjustment is applied. Repeated calls with confidence_adjustment=1.0 could push confidence_score above 1.0, or repeated -1.0 adjustments could push it below 0.0, corrupting the scoring model.",
  "why_builder_missed_it": "The builder validated the adjustment range but not the resulting value. The additive model was chosen for simplicity without considering cumulative drift.",
  "probe": "Ask the builder: If a hypothesis has confidence_score=0.8 and I call validate with confidence_adjustment=0.5, what is the resulting score? Is it clamped to 1.0?"
}
```

---

### V-018: Case Study Search Post-Filters Products and Tags in Python After Pagination

```json
{
  "severity": "low",
  "category": "logic",
  "location": "layer3-knowledge/src/services/case_study_service.py:352-362 (search method)",
  "finding": "The search method applies product and tag filters in Python AFTER fetching paginated results from Neo4j (lines 353-362). This means: (1) the total count is wrong — it reflects pre-filter count, (2) a page might return fewer items than the limit, and (3) some matching items on later pages are never seen. The comment says 'Post-filter by products and tags (Neo4j list operations)' acknowledging this is a workaround.",
  "why_builder_missed_it": "Neo4j list property filtering in WHERE clauses can be complex. The builder chose Python post-filtering for simplicity, not realizing it breaks pagination semantics.",
  "probe": "Ask the builder: If there are 100 case studies, limit=20, and the product filter matches only 3 items on page 1, the response shows total=100 but items has only 3 entries. Is this the intended behavior?"
}
```

---

### V-019: Competitive Landscape Query Missing Tenant Scope on Product Match

```json
{
  "severity": "low",
  "category": "logic",
  "location": "layer3-knowledge/src/services/competitive_intel_service.py:444-446 (analyze_competitive_landscape)",
  "finding": "When product_id is provided, the query uses `MATCH (p:Product {id: $product_id})-[cw:COMPETES_WITH]->(c)` without a tenant_id filter on the Product node (line 445). While the Competitor node is tenant-scoped (line 441), the Product match could theoretically match a product from another tenant if UUIDs collide or are guessed.",
  "why_builder_missed_it": "The builder added tenant scoping on the Competitor WHERE clause but missed adding it to the Product MATCH when product_id is specified. The non-product path uses OPTIONAL MATCH which is less risky.",
  "probe": "Ask the builder: In the product-specific landscape query, why doesn't the Product MATCH include tenant_id? Could a caller analyze competitive landscape using another tenant's product_id?"
}
```

---

### V-020: Hardcoded Contact Email in HTTP User-Agent

```json
{
  "severity": "low",
  "category": "secrets",
  "location": "layer4-agents/src/services/enrichment_orchestrator.py:135",
  "finding": "The HTTP client User-Agent header contains a hardcoded contact email: 'ValueFabric/1.0 (contact@valuefabric.io)'. While SEC EDGAR requires a contact email in User-Agent, hardcoding it in source code means it cannot be rotated without a code change and is exposed in the repository.",
  "why_builder_missed_it": "SEC EDGAR's API requires a User-Agent with contact info. The builder hardcoded it for simplicity rather than pulling from configuration/environment variables.",
  "probe": "Ask the builder: Should the User-Agent contact email come from an environment variable or configuration file rather than being hardcoded in source?"
}
```

---

### V-021: Test Files Mock All Security Boundaries — No Negative Security Tests

```json
{
  "severity": "low",
  "category": "logic",
  "location": "layer3-knowledge/tests/test_dil_phase1.py, test_dil_phase2.py; layer4-agents/tests/test_enrichment.py, test_value_hypothesis.py, test_dil_phase3.py",
  "finding": "All 156 tests mock the database/Neo4j layer and test only happy-path functionality. There are zero tests for: (1) missing X-Tenant-ID header, (2) cross-tenant access attempts, (3) invalid/malicious input values, (4) authentication enforcement, (5) authorization boundary violations. The test suite provides functional coverage but zero security assurance.",
  "why_builder_missed_it": "The builder was focused on proving the services work correctly. Security testing requires a different mindset (adversarial) and typically comes from a separate security testing phase that was not part of the build scope.",
  "probe": "Ask the builder: Are there any tests that verify a request without authentication is rejected? Any tests that verify Tenant-A cannot access Tenant-B's data?"
}
```

---

## Cross-Cutting Analysis

### Tenant Isolation Model

The entire DIL relies on a **trust-the-caller** tenant isolation model:

```
Client → [X-Tenant-ID: anything] → Route → Service → Database
                                      ↑
                              No auth check anywhere
```

There is no cryptographic binding between the caller's identity and the tenant they claim to represent. This is the single most impactful architectural gap.

### Attack Surface Summary

| Attack Vector | Endpoints Affected | Severity |
|--------------|-------------------|----------|
| Unauthenticated access | All ~50 endpoints | Critical |
| Tenant spoofing via header | All ~50 endpoints | Critical |
| IDOR via account UUID | 4 enrichment endpoints | Critical |
| SSRF via web crawl | POST /enrichment/{id} | High |
| Cypher property injection | PUT /competitive/competitors/{id} | High |
| Data poisoning via pre-fetched payloads | POST /narratives/generate | High |
| Pipeline data exfiltration | GET /intelligence/pipeline-summary | High |

### Dependency Observations

The code imports `httpx`, `neo4j`, `sqlalchemy`, `structlog`, `pydantic`, and `fastapi`. No pinned versions are visible in the DIL files themselves. The `httpx` client is used for outbound requests without TLS certificate verification configuration. The `neo4j` async driver is used throughout without connection pooling configuration visible in the DIL code.

---

## Recommendations Priority Matrix

| Priority | Action | Violations Addressed |
|----------|--------|---------------------|
| P0 (Immediate) | Add authentication middleware to all DIL routes | V-001, V-021 |
| P0 (Immediate) | Implement server-side tenant verification tied to auth identity | V-002, V-004, V-007, V-008 |
| P0 (Immediate) | Add tenant_id filter to all account lookups in enrichment | V-003 |
| P1 (This Sprint) | Add URL validation and SSRF protection to web crawl | V-005, V-015 |
| P1 (This Sprint) | Use allowlisted field names in dynamic Cypher SET clauses | V-006 |
| P1 (This Sprint) | Remove or gate pre-fetched data fields in narrative endpoint | V-010 |
| P2 (Next Sprint) | Add enum validation for status/outcome fields | V-011, V-016, V-017 |
| P2 (Next Sprint) | Fix pagination with server-side filtering | V-018 |
| P3 (Backlog) | Add security test suite | V-021 |
| P3 (Backlog) | Externalize configuration values | V-020 |

---

*This report catalogs violations only. Remediation recommendations are provided as priority guidance but detailed fix implementations are deferred pending builder review.*
