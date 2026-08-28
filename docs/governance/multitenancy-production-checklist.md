# Fabric_4L Multitenancy Production Checklist

The standard for Value Fabric multitenancy: **tenant isolation is an invariant enforced independently at every trust boundary, not a convention propagated through application code.**

---

## Multitenancy Production Checklist

### 1. Tenant Identity and Request Context

- [ ] Every authenticated request resolves exactly one canonical `tenant_id`
- [ ] `tenant_id` comes from trusted authorization/session state, not user-controlled request fields
- [ ] Caller-supplied `tenant_id` is rejected or ignored where identity is already established
- [ ] Tenant context is immutable for the lifetime of a request
- [ ] Missing tenant context fails closed
- [ ] Invalid/unknown tenants fail closed
- [ ] Suspended/deactivated tenants fail closed
- [ ] Cross-tenant impersonation requires an explicit privileged workflow
- [ ] Administrative impersonation is auditable
- [ ] Background jobs carry tenant identity explicitly
- [ ] WebSocket/session connections bind tenant identity at establishment
- [ ] Service-to-service calls propagate authenticated tenant context
- [ ] Tenant context cannot be overridden by arbitrary headers

### 2. Authorization

- [ ] Authentication and tenant authorization are separate checks
- [ ] Every tenant-scoped resource performs tenant authorization before access
- [ ] Object authorization checks both resource ID and tenant ownership
- [ ] Authorization happens before business logic
- [ ] Authorization happens before sensitive existence checks
- [ ] Unauthorized access does not reveal whether another tenant's object exists
- [ ] Role/permission lookup is tenant-scoped
- [ ] Users belonging to multiple tenants receive explicit tenant selection
- [ ] Cross-tenant administrative permissions are explicitly modeled
- [ ] No implicit "superuser" paths bypass tenant enforcement
- [ ] Authorization snapshot/cache includes tenant identity
- [ ] Expired authorization state fails closed

*Note for Fabric 4L:* Authorization snapshot should remain the backend source of truth rather than trusting frontend route state.

---

### 3. API and Routing Boundary

For every endpoint:

- [ ] Tenant ownership is validated for all path parameters
- [ ] Tenant ownership is validated for query-selected resources
- [ ] Tenant ownership is validated for nested resources
- [ ] POST cannot create a child beneath another tenant's parent
- [ ] PUT/PATCH cannot re-parent a resource into another tenant
- [ ] DELETE verifies tenant ownership
- [ ] Bulk operations validate every object
- [ ] Search endpoints automatically constrain by tenant
- [ ] Pagination cannot cross tenant boundaries
- [ ] Export endpoints are tenant-scoped
- [ ] Import endpoints assign the authenticated tenant
- [ ] File download URLs are tenant-scoped
- [ ] Graph endpoints are tenant-scoped
- [ ] Health/debug endpoints expose no tenant data

**Critical test:**
`tenant A credentials + tenant B resource ID -> denied` (must exist for every resource family).

---

### 4. Database Enforcement

Application checks alone are insufficient.

#### PostgreSQL / Relational

- [ ] Every tenant-owned table contains a non-nullable `tenant_id`
- [ ] Foreign keys preserve tenant ownership
- [ ] Composite relationships include tenant identity where appropriate
- [ ] Row-Level Security (RLS) is enabled on tenant-owned tables
- [ ] RLS policies exist for SELECT
- [ ] RLS policies exist for INSERT
- [ ] RLS policies exist for UPDATE
- [ ] RLS policies exist for DELETE
- [ ] Production application roles cannot bypass RLS
- [ ] Table owners are not accidentally used by the application
- [ ] `BYPASSRLS` is unavailable to runtime roles
- [ ] Migration tooling is separated from runtime credentials
- [ ] Tenant context is set transactionally
- [ ] Connection pooling cannot leak tenant session state
- [ ] Failed transactions cannot leave stale tenant context behind
- [ ] Database views preserve tenant restrictions
- [ ] Materialized views preserve tenant restrictions
- [ ] Stored procedures enforce tenant isolation

#### Schema Invariant

For tenant-owned parent/child objects, prefer constraints equivalent to:

```text
(parent_id, tenant_id) -> (parent.id, parent.tenant_id)
```

rather than only:

```text
parent_id -> parent.id
```

This makes cross-tenant parent-child relationships structurally impossible (GAP-01 mitigation).

---

### 5. Graph Database / Layer 3 (Neo4j)

- [ ] Every tenant-owned node contains canonical `tenant_id`
- [ ] Tenant ownership cannot be supplied by arbitrary model input
- [ ] Every node lookup constrains tenant
- [ ] Every relationship creation verifies both endpoints have the same tenant
- [ ] Traversals start from a tenant-scoped root
- [ ] Traversals cannot cross tenant boundaries
- [ ] Variable-length traversals remain tenant constrained
- [ ] `MATCH` queries include tenant constraints
- [ ] `MERGE` keys include tenant where necessary
- [ ] Dynamic Cypher cannot bypass tenant enforcement
- [ ] Bulk synchronization preserves tenant identity
- [ ] Graph projections/analytics are tenant-scoped
- [ ] Tenant deletion removes tenant graph state
- [ ] Cross-tenant graph edges are structurally tested

**High-value invariant:**
```text
No relationship may connect two tenant-owned nodes where source.tenant_id != target.tenant_id.
```

---

### 6. Redis, Caching, and Ephemeral State

- [ ] Every tenant-sensitive cache key includes `tenant_id`
- [ ] Cache namespaces cannot collide
- [ ] Authorization caches include tenant
- [ ] Search-result caches include tenant
- [ ] LLM-response caches include tenant where inputs are tenant-sensitive
- [ ] Idempotency keys are tenant-scoped
- [ ] Distributed locks are tenant-scoped
- [ ] Rate-limit keys have deliberate tenant/user semantics
- [ ] Session state is tenant-bound
- [ ] Cache invalidation cannot flush or expose another tenant unintentionally
- [ ] No global "latest object" cache for tenant-owned resources

**Preferred key format:**
```text
tenant:{tenant_id}:resource:{resource_id}
```
instead of `resource:{resource_id}`.

---

### 7. Background Jobs and Queues

- [ ] Every job payload contains trusted tenant identity
- [ ] Workers reject missing tenant identity
- [ ] Worker runtime reconstructs tenant authorization context
- [ ] Job retries preserve tenant identity
- [ ] Dead-letter queue entries preserve tenant identity
- [ ] Scheduled tasks operate per tenant or explicitly globally
- [ ] Batch jobs cannot aggregate tenant data accidentally
- [ ] Fan-out jobs maintain tenant partitioning
- [ ] Job deduplication includes tenant identity
- [ ] Temporal/workflow state is tenant-scoped
- [ ] Workflow child processes inherit tenant context

---

### 8. LLM / Agent Isolation (Layer 4)

- [ ] Every agent invocation has tenant context
- [ ] Agent tools do not accept arbitrary tenant overrides
- [ ] Retrieval is tenant-scoped before context reaches the model
- [ ] Vector searches are tenant-filtered
- [ ] Knowledge graph tools enforce tenant isolation independently
- [ ] Tool calls re-authorize resource access
- [ ] Memory/checkpoint state is tenant-scoped
- [ ] Conversation history is tenant-scoped
- [ ] Agent state stores tenant identity
- [ ] LangGraph checkpoint keys include tenant
- [ ] Prompt caches cannot leak cross-tenant context
- [ ] Agent traces/logs preserve tenant identity without exposing sensitive content
- [ ] Model-generated IDs cannot be trusted as authorization
- [ ] Caller-supplied "truth" cannot override tenant ownership
- [ ] Synthetic fallback cannot fabricate cross-tenant evidence
- [ ] Evidence IDs resolve only inside the same tenant

*Core rule:* A model should never be part of the tenant authorization decision.

---

### 9. Embeddings / Vector Stores

- [ ] Embeddings include tenant metadata
- [ ] Retrieval always filters tenant before ranking
- [ ] Tenant filtering occurs server-side
- [ ] Similarity search cannot return unfiltered global candidates
- [ ] Namespace/collection separation is documented
- [ ] Reindexing preserves tenant metadata
- [ ] Deleted tenant embeddings disappear
- [ ] Evaluation datasets cannot mix production tenants
- [ ] Shared embeddings contain only intentionally global knowledge

---

### 10. Files and Object Storage

- [ ] Storage keys contain tenant namespace
- [ ] Upload ownership derives from authenticated tenant
- [ ] Download authorization occurs server-side
- [ ] Presigned URLs have short expiry
- [ ] Presigned URLs cannot be generated for another tenant's object
- [ ] Object metadata includes tenant
- [ ] Background document processing retains tenant
- [ ] OCR/parsing jobs retain tenant
- [ ] Temporary files are tenant-isolated
- [ ] Cleanup jobs cannot delete another tenant's files
- [ ] CDN caching does not make private files globally accessible

---

### 11. Search

- [ ] Full-text indexes contain tenant metadata
- [ ] Every search query filters tenant
- [ ] Autocomplete is tenant-scoped
- [ ] Suggestions are tenant-scoped
- [ ] Search counts do not leak global corpus sizes
- [ ] Facets are tenant-scoped
- [ ] Saved searches are tenant-owned

---

### 12. Vendor / External Provider Isolation

- [ ] Provider calls carry only minimum necessary tenant data
- [ ] Vendor responses are assigned tenant provenance on ingestion
- [ ] Vendor identifiers are not treated as tenant identifiers
- [ ] Provider response caches are deliberately global or tenant-scoped
- [ ] Shared third-party data is explicitly classified
- [ ] Tenant-private enrichment is never reused globally
- [ ] Webhook payloads resolve tenant through trusted mappings
- [ ] Provider callbacks cannot select arbitrary tenants
- [ ] Retry queues preserve tenant context
- [ ] Provenance records include tenant ownership

*Architectural rule:* External providers supply observations; Fabric assigns tenant ownership and economic meaning.

---

### 13. Webhooks

- [ ] Webhook secret maps to a known tenant/integration
- [ ] Tenant cannot be taken directly from webhook JSON
- [ ] Signature verification happens before processing
- [ ] Timestamp freshness is enforced
- [ ] Replay attacks are rejected
- [ ] Idempotency keys are tenant-scoped
- [ ] Duplicate webhook processing cannot cross tenants
- [ ] Retry handling preserves tenant mapping
- [ ] Unknown integrations fail closed

---

### 14. Logging, Telemetry, and Observability

- [ ] Logs include tenant correlation identifier where appropriate
- [ ] Logs do not expose tenant secrets
- [ ] Tenant data is not accidentally aggregated into user-visible telemetry
- [ ] Trace attributes contain tenant safely
- [ ] Metrics labels avoid high-cardinality mistakes
- [ ] Admin dashboards enforce tenant permissions
- [ ] Error-reporting tools cannot expose one tenant's payloads to another
- [ ] Support tooling records all cross-tenant access
- [ ] Audit logs cannot be modified by tenants

---

### 15. Billing / Metering

- [ ] Usage events contain canonical tenant ID
- [ ] Usage cannot be attributed from user-controlled metadata
- [ ] Meter aggregation groups by tenant
- [ ] Credits/limits are tenant-scoped
- [ ] Idempotent usage events are tenant-scoped
- [ ] Billing exports cannot include other tenants
- [ ] Legacy/canonical billing paths use the same tenant authority
- [ ] Administrative corrections are audited

---

### 16. Frontend

Frontend checks are UX protections, not security controls.

- [ ] Active tenant is explicit in frontend state
- [ ] Tenant switch clears tenant-sensitive query caches
- [ ] Tenant switch clears stale forms
- [ ] Tenant switch clears subscriptions/WebSockets
- [ ] Browser storage is tenant-namespaced
- [ ] TanStack Query keys include tenant where required
- [ ] Optimistic updates cannot affect another tenant's cache
- [ ] Deep links revalidate tenant authorization
- [ ] URL tenant identifiers are never independently trusted
- [ ] Route guards use backend authorization state

---

### 17. Cross-Tenant Parent/Child Invariants

For each Fabric resource family:
- Signal
- ValueDriver
- Hypothesis
- Stakeholder
- FormulaVariable
- IngestionJob
- TaskItem
- BusinessCase
- Evidence
- Account
- Product
- Deliverable
- Pipeline run
- Graph entity

Verify all four:
```text
CREATE: Tenant A cannot create child beneath Tenant B parent.
READ:   Tenant A cannot retrieve Tenant B child.
UPDATE: Tenant A cannot move its child beneath Tenant B parent.
DELETE: Tenant A cannot delete Tenant B child.
```

---

### 18. Test Strategy

Three mandatory test classes:

#### A. Resource Isolation Contract Tests
For every resource:
```text
tenant_A_token + tenant_A_resource -> allowed
tenant_A_token + tenant_B_resource -> denied
tenant_B_token + tenant_A_resource -> denied
missing_tenant -> denied
invalid_tenant -> denied
```

#### B. Structural Database Tests
Prove that invalid state cannot exist: `child.tenant_id != parent.tenant_id` must fail at the persistence boundary.

#### C. End-to-End Adversarial Tests
Run full workflows using two simultaneously populated tenants and intentionally try to leak across boundaries.

---

### 19. Cross-Layer Invariant Testing

Fabric must maintain a canonical security suite that traverses L1–L7:

```text
Tenant A ingestion -> Extraction -> Knowledge Graph -> Agent -> Review -> Deliverable -> Billing
```

At every transition:
```text
input tenant == persisted tenant == retrieved tenant
```
and:
```text
No artifact reachable by Tenant A may depend on Tenant B private state.
```

The cross-layer isolation suite must be treated as release-blocking security debt, not ordinary test debt.

---

### 20. CI Gates

Mandatory automated checks:

- [ ] Tenant invariant unit tests
- [ ] Database RLS tests
- [ ] Parent-child schema integrity tests
- [ ] Cross-layer isolation tests
- [ ] Graph isolation tests
- [ ] Cache isolation tests
- [ ] Background-job tenant propagation tests
- [ ] LLM retrieval isolation tests
- [ ] Webhook tenant-resolution tests
- [ ] Bulk endpoint tenant-isolation tests
- [ ] Search/vector tenant-filter tests
- [ ] Static scan for unscoped repository queries
- [ ] Static scan for caller-supplied tenant authority
- [ ] Migration validation for missing `tenant_id`
- [ ] No skipped P0 isolation tests
- [ ] No `xfail` of required tenant invariants
- [ ] Production readiness gate fails if isolation suite does not execute

*Rule:* A skipped security test does not count as passing.

---

### 21. Static Architecture Rules

Automated checks forbidding patterns such as:
```python
Repository.get(id)  # FORBIDDEN for tenant-owned resources
```
in favor of:
```python
Repository.get(tenant_id, id)  # REQUIRED
```

Similarly forbid `WHERE id = :id` where the underlying entity is tenant-owned unless verified RLS is proven. Preferred repository interfaces:
```python
get_for_tenant(tenant_id, resource_id)
list_for_tenant(tenant_id)
delete_for_tenant(tenant_id, resource_id)
```

---

### 22. Tenant Lifecycle

- [ ] Tenant creation initializes required security state
- [ ] Tenant suspension immediately blocks access
- [ ] Tenant deletion is defined
- [ ] Soft-deleted tenants remain inaccessible
- [ ] Tenant data export is complete
- [ ] Tenant deletion covers SQL, Neo4j, Redis, vectors, files, checkpoints, and vendor mappings
- [ ] Backups have a defined tenant deletion/retention policy

---

### 23. Backup / Restore

- [ ] Restore cannot merge tenants incorrectly
- [ ] Tenant IDs remain stable across restore
- [ ] Point-in-time recovery preserves tenant relationships
- [ ] Per-tenant recovery strategy is documented
- [ ] Backup access is restricted
- [ ] Backup data receives the same confidentiality classification as production

---

### 24. Operational / Support Access

- [ ] Support personnel do not implicitly receive all-tenant access
- [ ] Break-glass access is explicit, time-limited, and audited
- [ ] Tenant impersonation shows visible operator context
- [ ] Support exports are audited
- [ ] Production database consoles do not default to unrestricted runtime access

---

### 25. Release-Blocking Invariants (P0 Non-Negotiables)

1. **No caller-supplied tenant truth.**
2. **Every tenant-owned persistent object has canonical tenant ownership.**
3. **Every persistent boundary independently enforces tenant isolation.**
4. **Parent and child tenant IDs can never disagree.**
5. **Every query is tenant constrained or protected by verified RLS.**
6. **Every async/background execution preserves authenticated tenant context.**
7. **Graph traversals cannot cross tenant boundaries.**
8. **Vector/search retrieval cannot cross tenant boundaries.**
9. **Agent tools independently re-enforce tenant authorization.**
10. **No P0 tenant-isolation test may be skipped.**
11. **Cross-layer isolation must execute in CI, not merely exist in the repository.**
12. **A security control is not "implemented" until it is exercised against the production-equivalent persistence/runtime path.**

---

## Definition of Done

Multitenancy is production-ready when:

```text
Authentication
+ Authorization
+ Application scoping
+ Persistence enforcement
+ Async propagation
+ Cache isolation
+ Graph isolation
+ Retrieval isolation
+ Agent/tool isolation
+ Adversarial tests
+ Mandatory CI execution
= Tenant boundary
```
