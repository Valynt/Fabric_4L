# API Contract Stability Guidelines

## 1. Purpose

This document defines a practical, production-grade API contract stability strategy for Fabric_4L. It ensures REST API contracts remain stable across versions, clients experience minimal breaking changes, and every contract change is governed, tested, documented, and communicated. Fabric_4L APIs are consumed by multiple clients including the frontend, internal services, agents, SDKs, tests, and potentially future third-party systems. Breaking API contracts can cause outages, failed workflows, support burden, and loss of trust. This document provides the strategy for REST API versioning, backward compatibility, forward compatibility, schema evolution, deprecation, and automated contract checks.

## 2. Scope

**Primary Scope:**
- RESTful HTTP APIs across Layers 1–6
- Public and internal APIs
- Existing `/api/v1` convention
- API versioning strategy
- Backward and forward compatibility
- Schema evolution
- Endpoint and field deprecation
- OpenAPI/schema hygiene
- Automated contract testing and CI checks
- Consumer communication process

**Out of Scope:**
- Agent tool contracts in `contracts/tool-manifests/` (mentioned in Section 18 as adjacent surface)
- Complete API architecture redesign
- Replacement of `contracts/GOVERNANCE.md`
- Replacement of existing pytest contract tests in `tests/contract/`

## 3. Relationship to Existing Contract Governance

This document is the **practical implementation guide** for API contract stability. It complements, but does not replace, the high-level authority defined in:

- **`contracts/GOVERNANCE.md`** - The Contract Council RFC process, breaking changes policy, and emergency hotfix procedures remain the authoritative governance document.
- **`contracts/frontend/01-api-boundary-contract.md`** - The frontend-backend HTTP communication contract (error shape, pagination, retry policy) remains the contract for frontend integration.
- **`tests/contract/`** - The existing pytest contract test infrastructure remains the baseline for automated contract validation.

This document fills the gap between high-level governance and day-to-day engineering decisions by providing:
- Concrete versioning policy for the `/api/v1` convention
- Detailed breaking change criteria with examples
- Schema evolution rules for DTOs and OpenAPI
- Deprecation timelines and communication templates
- CI/CD enforcement patterns
- Practical checklists for engineers

## 4. Core Principles

Fabric_4L API contract stability is built on these principles:

### 4.1 Stability by Default
- Existing API contracts must not change without explicit justification
- Clients should be able to upgrade Fabric_4L without breaking their integrations
- Backward compatibility is the default assumption for all changes

### 4.2 Additive Change Preference
- Prefer adding new optional fields, new endpoints, or new enum values over breaking changes
- Additive changes allow old clients to continue working while new clients can adopt new features
- Breaking changes should be rare and require version bumps

### 4.3 Explicit Versioning for Breaking Changes
- Never break existing API contracts without an explicit, well-communicated version change
- Use semantic versioning principles to distinguish breaking from non-breaking changes
- Keep `/api/v1` stable unless a breaking change justifies a future `/api/v2`

### 4.4 OpenAPI as Source of Machine-Readable Truth
- OpenAPI specs in `contracts/openapi/` are the authoritative contract definition
- Human-readable documentation (e.g., `docs/API_REFERENCE.md`) must stay in sync with OpenAPI
- Generated clients (TypeScript, Python, etc.) are derived from OpenAPI, not hand-written

### 4.5 Consumer-First Change Management
- Consider all consumers (frontend, agents, SDKs, tests, third parties) before changing contracts
- Provide migration paths for deprecated endpoints, fields, enum values, or response shapes
- Communicate changes early and clearly with appropriate lead time

### 4.6 CI-Enforced Contract Safety
- Automate contract checks in CI/CD pipelines
- Detect contract drift before merge
- Block breaking changes without explicit approval
- Require OpenAPI updates alongside implementation changes

### 4.7 Tenant/Security Invariants Cannot Be Bypassed for Compatibility
- Do not weaken security, tenant isolation, or error-envelope requirements for compatibility
- Do not return raw exceptions or unstable error shapes
- Authentication and authorization requirements are non-negotiable
- Tenant context injection (`X-Tenant-ID`) must remain enforced

## 5. API Versioning Policy

### 5.1 Current Convention: `/api/v1`

All Fabric_4L layers currently use the `/api/v1` URI prefix:

| Layer | Base Path | Port |
|-------|-----------|------|
| Layer 1 | `/api/v1/ingestion` | 8001 |
| Layer 2 | `/api/v1/extraction` | 8002 |
| Layer 3 | `/v1` | 8003 |
| Layer 4 | `/api/v1` | 8004 |
| Layer 5 | `/api/v1` | 8005 |
| Layer 6 | `/v1/benchmarks` | 8006 |

**Note:** Layers 3 and 6 use `/v1` instead of `/api/v1` for historical reasons. This inconsistency should be addressed in a future coordinated effort, but does not block contract stability work.

### 5.2 When to Remain in `/api/v1`

Stay in `/api/v1` for:
- **Additive changes:** New optional fields, new endpoints, new enum values
- **Bug fixes:** Correcting behavior that was clearly broken (not semantic changes)
- **Performance improvements:** Changes that do not affect contract shape
- **Documentation updates:** Clarifying existing behavior without changing it
- **Internal refactoring:** Changes invisible to clients (e.g., database schema changes)

### 5.3 When `/api/v2` is Justified

Create `/api/v2` only for:
- **Breaking changes that cannot be avoided:** Removing endpoints, renaming fields, changing field types, making optional fields required
- **Major architectural shifts:** Changes that fundamentally alter the API model
- **Security requirements:** Changes that require different authentication or authorization patterns

**Examples justifying `/api/v2`:**
- Removing a widely-used endpoint
- Changing the response shape of a core workflow endpoint
- Switching from offset-based to cursor-based pagination
- Requiring a new authentication mechanism

**Examples NOT justifying `/api/v2`:**
- Adding a new optional field to a response
- Adding a new endpoint alongside existing ones
- Fixing a bug where the API returned incorrect data
- Improving error messages without changing error codes

### 5.4 Why Not Create New Versions for Every Small Change

Creating new API versions for every change causes:
- **Fragmentation:** Clients must track and test against multiple versions
- **Maintenance burden:** Supporting multiple versions indefinitely increases complexity
- **Confusion:** Unclear which version clients should use
- **Slow adoption:** Clients delay upgrades when versions change frequently

**Rule:** Prefer additive changes within the current version. Only bump versions when absolutely necessary.

### 5.5 URI Versioning as Current Baseline

Fabric_4L currently uses URI versioning (e.g., `/api/v1/ingestion/targets`). This is the baseline and should remain the primary versioning strategy.

**Advantages of URI versioning:**
- Clear and explicit in the URL
- Easy to route and monitor
- Works with all HTTP clients
- Simple to document

### 5.6 Header/Media-Type Versioning as Future Optional Consideration

Future enhancements could consider header-based versioning (e.g., `Accept: application/vnd.fabric.v1+json`) or media-type versioning for specific use cases, but this should be evaluated separately and not adopted without explicit justification.

### 5.7 Semantic Versioning Principles for Schemas and Generated Clients

While the URI version is coarse-grained (`/api/v1`), individual schemas and generated clients should follow semantic versioning principles:

- **MAJOR version:** Breaking changes to schema structure
- **MINOR version:** Additive changes (new optional fields, new endpoints)
- **PATCH version:** Bug fixes, documentation updates

This allows consumers to track changes at a finer granularity than the URI version.

## 6. What Counts as a Breaking Change

A breaking change is any modification that would cause an existing, compliant client to fail or behave incorrectly.

### 6.1 Endpoint Changes

**Breaking:**
- Removing an endpoint
- Renaming an endpoint (changes the URL)
- Changing the HTTP method (e.g., GET to POST)
- Removing support for a previously accepted HTTP method

**Example:**
```python
# BEFORE (breaking to remove)
GET /api/v1/workflows/{id}

# AFTER (breaking - endpoint removed)
# Endpoint no longer exists
```

### 6.2 Field Changes

**Breaking:**
- Renaming a field in request or response
- Changing a field type (e.g., `string` to `number`, `integer` to `float`)
- Making an optional field required
- Removing a field from response
- Changing the structure of a field (e.g., object to array)
- Changing the nullability of a field (nullable to non-nullable)

**Examples:**
```json
// BEFORE (breaking to rename)
{
  "workflow_id": "uuid",
  "status": "running"
}

// AFTER (breaking - field renamed)
{
  "id": "uuid",           // was "workflow_id"
  "status": "running"
}
```

```json
// BEFORE (breaking to change type)
{
  "progress_percentage": 65
}

// AFTER (breaking - type changed)
{
  "progress_percentage": "65%"  // was integer, now string
}
```

```json
// BEFORE (breaking to make required)
{
  "workflow_type": "roi_calculator",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "inputs": {}
}

// AFTER (breaking - new required field)
{
  "workflow_type": "roi_calculator",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "inputs": {},
  "priority": "NORMAL"  // new required field
}
```

### 6.3 Enum Changes

**Breaking:**
- Removing an enum value
- Renaming an enum value
- Changing the numeric value of an enum (if using numeric enums)

**Example:**
```python
# BEFORE (breaking to remove value)
class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# AFTER (breaking - value removed)
class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    # FAILED removed
```

### 6.4 Pagination Changes

**Breaking:**
- Changing the pagination shape (e.g., from offset-based to cursor-based)
- Removing pagination parameters
- Changing the default page size
- Changing the maximum page size
- Removing `has_next` or similar navigation fields

**Example:**
```json
// BEFORE (breaking to change shape)
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 25,
  "has_next": true
}

// AFTER (breaking - shape changed)
{
  "items": [...],
  "next_cursor": "abc123",
  "has_more": true
}
```

### 6.5 Error Envelope Changes

**Breaking:**
- Changing the error envelope structure defined in `contracts/frontend/01-api-boundary-contract.md`
- Removing standard error fields (`code`, `message`, `details`)
- Changing the error code format
- Removing the `error` wrapper

**Example:**
```json
// BEFORE (breaking to change envelope)
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": {}
  }
}

// AFTER (breaking - envelope changed)
{
  "errorCode": "VALIDATION_ERROR",
  "errorMessage": "Invalid input"
}
```

### 6.6 Authentication and Tenant Context Changes

**Breaking:**
- Changing authentication requirements (e.g., adding required headers)
- Changing the JWT token format or validation rules
- Removing support for `X-Tenant-ID` header
- Changing tenant isolation behavior
- Adding new required scopes or permissions

**Example:**
```python
# BEFORE (breaking to change auth)
# Requires: Authorization header, X-Tenant-ID header

# AFTER (breaking - new required header)
# Requires: Authorization header, X-Tenant-ID header, X-Request-ID header
```

### 6.7 HTTP Status Code Changes

**Breaking:**
- Changing a status code in a way clients rely on (e.g., 201 to 200)
- Returning a different status code for the same input
- Removing a status code that clients handle specifically

**Example:**
```python
# BEFORE (breaking to change status)
POST /api/v1/workflows -> 201 Created

# AFTER (breaking - status changed)
POST /api/v1/workflows -> 200 OK
```

### 6.8 Semantic Meaning Changes

**Breaking:**
- Changing the semantic meaning of an existing field without changing its name or type
- Changing the units of a numeric field (e.g., seconds to milliseconds)
- Changing the format of a string field (e.g., ISO 8601 to Unix timestamp)
- Changing the interpretation of a boolean flag

**Example:**
```json
// BEFORE (breaking to change semantics)
{
  "progress_percentage": 65  // 0-100 scale
}

// AFTER (breaking - semantics changed)
{
  "progress_percentage": 0.65  // 0.0-1.0 scale
}
```

## 7. Safe Additive Changes

Additive changes allow old clients to continue working while new clients can adopt new features. These are preferred over breaking changes.

### 7.1 Adding a New Optional Response Field

**Safe:**
```json
// BEFORE
{
  "workflow_id": "uuid",
  "status": "running"
}

// AFTER (safe - new optional field)
{
  "workflow_id": "uuid",
  "status": "running",
  "estimated_completion_seconds": 30  // new optional field
}
```

Old clients ignore the new field. New clients can use it if present.

### 7.2 Adding a New Endpoint

**Safe:**
```python
# BEFORE
GET /api/v1/workflows/{id}

# AFTER (safe - new endpoint)
GET /api/v1/workflows/{id}
GET /api/v1/workflows/{id}/summary  # new endpoint
```

Old clients continue using the existing endpoint. New clients can use the new endpoint.

### 7.3 Adding a New Optional Request Field

**Safe:**
```json
// BEFORE
{
  "workflow_type": "roi_calculator",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "inputs": {}
}

// AFTER (safe - new optional field)
{
  "workflow_type": "roi_calculator",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "inputs": {},
  "priority": "NORMAL"  # new optional field with default
}
```

Old clients omit the field and get default behavior. New clients can specify it.

### 7.4 Adding Enum Values (With Client Tolerance)

**Safe only if clients are designed to tolerate unknown values:**
```python
# BEFORE
class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"

# AFTER (safe - new value added)
class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"  # new value
```

**Condition:** This is safe only if clients handle unknown enum values gracefully (e.g., by treating them as "unknown" rather than erroring). If clients have strict enum validation, this is breaking.

### 7.5 Adding Metadata Fields

**Safe:**
```json
// BEFORE
{
  "workflow_id": "uuid",
  "status": "running"
}

// AFTER (safe - metadata field)
{
  "workflow_id": "uuid",
  "status": "running",
  "_metadata": {
    "version": "1.0.0",
    "generated_at": "2025-01-01T00:00:00Z"
  }
}
```

Metadata fields (prefixed with `_`) are conventionally ignored by clients that don't understand them.

### 7.6 Adding New Filter Parameters with Default-Compatible Behavior

**Safe:**
```python
# BEFORE
GET /api/v1/workflows

# AFTER (safe - new filter parameter)
GET /api/v1/workflows?status=running  # new parameter, defaults to all if omitted
```

Old clients omit the parameter and get all results. New clients can filter.

## 8. Schema Evolution Rules

### 8.1 Request DTO Rules

**Allowed:**
- Add new optional fields with default values
- Add new optional fields without defaults (server handles absence)
- Relax validation (e.g., increase max length, allow more values)
- Add new enum values (if clients tolerate unknown values)

**Not Allowed:**
- Remove fields
- Rename fields
- Change field types
- Make optional fields required
- Tighten validation (e.g., decrease max length, restrict enum values)
- Change field nullability

**Example:**
```python
# Safe request DTO evolution
class WorkflowCreateRequest(BaseModel):
    workflow_type: str
    tenant_id: str
    user_id: str
    inputs: dict
    priority: str = "NORMAL"  # safe: new optional field with default
    tags: Optional[List[str]] = None  # safe: new optional field
```

### 8.2 Response DTO Rules

**Allowed:**
- Add new optional fields
- Add new fields with computed values
- Add metadata fields
- Relax validation on returned values

**Not Allowed:**
- Remove fields
- Rename fields
- Change field types
- Change field nullability (nullable to non-nullable)
- Change the structure of nested objects
- Remove or change enum values

**Example:**
```python
# Safe response DTO evolution
class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str
    workflow_type: str
    status: str
    current_state: str
    progress_percentage: int
    estimated_completion_seconds: Optional[int] = None  # safe: new optional field
    _metadata: Optional[dict] = None  # safe: metadata field
```

### 8.3 Enum Rules

**Allowed:**
- Add new enum values (if clients tolerate unknown values)
- Add enum aliases (same value, different name)

**Not Allowed:**
- Remove enum values
- Rename enum values
- Change numeric values of enums
- Reorder enum values if order matters to clients

**Example:**
```python
# Safe enum evolution
class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"  # safe: new value added
```

### 8.4 Error Envelope Rules

**Allowed:**
- Add new optional fields to `error.details`
- Add new error codes (if clients handle unknown codes gracefully)
- Improve error messages (more descriptive, same code)

**Not Allowed:**
- Change the error envelope structure
- Remove standard fields (`code`, `message`, `details`)
- Change error code format
- Remove error codes

**Example:**
```json
// Safe error envelope evolution
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": {
      "field_errors": {...},
      "request_id": "uuid"  # safe: new optional detail
    }
  }
}
```

### 8.5 Pagination Rules

**Allowed:**
- Add new pagination parameters with defaults
- Add new navigation fields (e.g., `previous_cursor`)
- Change default page size (if clients respect page_size parameter)

**Not Allowed:**
- Change pagination shape (offset to cursor or vice versa)
- Remove pagination parameters
- Remove navigation fields (`has_next`, `next_cursor`)
- Change the meaning of existing parameters

**Example:**
```json
// Safe pagination evolution
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 25,
  "has_next": true,
  "previous_cursor": "xyz789"  // safe: new navigation field
}
```

### 8.6 ID and Timestamp Rules

**Allowed:**
- Add new ID fields (e.g., add `slug` alongside `id`)
- Add new timestamp fields (e.g., add `updated_at` alongside `created_at`)
- Change timestamp format to ISO 8601 if already using ISO 8601

**Not Allowed:**
- Change ID format (e.g., UUID to integer)
- Remove ID fields
- Change timestamp format (e.g., ISO 8601 to Unix timestamp)
- Remove timestamp fields

**Example:**
```json
// Safe ID/timestamp evolution
{
  "id": "uuid",
  "slug": "workflow-name",  // safe: new ID field
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-02T00:00:00Z"  // safe: new timestamp field
}
```

### 8.7 Nullable Fields

**Allowed:**
- Change a non-nullable field to nullable (add `Optional`)
- Add default values for nullable fields

**Not Allowed:**
- Change a nullable field to non-nullable (remove `Optional`)

**Example:**
```python
# Safe nullable evolution
class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    completed_at: Optional[str] = None  # safe: nullable field
```

### 8.8 Default Values

**Allowed:**
- Add default values to optional fields
- Change default values (if clients don't rely on specific defaults)

**Not Allowed:**
- Remove default values (making fields required)
- Change default values if clients rely on specific defaults

**Example:**
```python
# Safe default value evolution
class WorkflowCreateRequest(BaseModel):
    workflow_type: str
    priority: str = "NORMAL"  # safe: default value
```

### 8.9 Field Deprecation Markers

When deprecating fields (before removal), use OpenAPI deprecation:

```yaml
# OpenAPI example
deprecated_field:
  type: string
  description: Deprecated field. Use new_field instead.
  deprecated: true
  x-deprecated-since: "2025-01-01"
  x-removal-target: "2025-06-01"
  x-replacement-field: "new_field"
```

### 8.10 OpenAPI Schema Requirements

**Required:**
- All endpoints must be documented in OpenAPI
- All request/response schemas must be defined
- All fields must have types and descriptions
- Deprecated fields must be marked with `deprecated: true`
- All changes must be reflected in OpenAPI before merge

**Validation:**
- OpenAPI specs must be valid (use `spectral lint` or similar)
- OpenAPI specs must be consistent with implementation
- Generated clients must build successfully

## 9. Deprecation Policy

### 9.1 Deprecation Notice Requirements

All deprecations must include:
- **Clear notice:** What is being deprecated (endpoint, field, enum value)
- **Reason:** Why it is being deprecated
- **Replacement:** What to use instead
- **Timeline:** When it will be removed
- **Migration guide:** How to update client code

### 9.2 Minimum Deprecation Windows

| API Type | Minimum Window | Recommended Window |
|----------|----------------|-------------------|
| Public APIs | 6 months | 12 months |
| Internal APIs | 3 months | 6 months |
| Beta/Experimental APIs | 1 month | 3 months |

**Note:** These are minimums. Complex changes or widely-used features may require longer windows.

### 9.3 Public vs Internal API Differences

**Public APIs:**
- Require longer deprecation windows (minimum 6 months)
- Require public announcements (blog posts, email notifications)
- Require detailed migration guides
- Require support during migration period
- May require multiple reminder communications

**Internal APIs:**
- Shorter deprecation windows acceptable (minimum 3 months)
- Internal communication only (Slack, email, team meetings)
- Migration guides can be less detailed
- Direct support available to internal teams
- Single communication often sufficient

### 9.4 Migration Path Requirements

Every deprecation must include a migration path:
- **Direct replacement:** Use field X instead of field Y
- **Code change:** Update client code to call new endpoint
- **Configuration change:** Update environment variables or config files
- **Data migration:** Run a migration script if needed

**Example:**
```markdown
## Deprecation: POST /v1/query

**Deprecated Since:** 2026-04-14
**Removal Target:** 2026-08-01
**Replacement:** POST /v1/query/graph

### Migration Guide

Update your client code to use the new endpoint:

```python
# OLD (deprecated)
response = requests.post("https://api.example.com/v1/query", {...})

# NEW (replacement)
response = requests.post("https://api.example.com/v1/query/graph", {...})
```

The new endpoint accepts the same request payload and returns the same response shape.
```

### 9.5 Deprecation Headers

Deprecated endpoints should emit deprecation headers:

```http
Warning: 299 - "This endpoint is deprecated. Use POST /v1/query/graph instead."
X-Deprecated-Since: 2026-04-14
X-Target-Removal-Date: 2026-08-01
X-Deprecation-Owner: platform-team
X-Deprecation-Docs: https://docs.example.com/api/deprecations/query-endpoint
```

### 9.6 Documentation Requirements

Deprecations must be documented in:
- **OpenAPI spec:** Mark endpoint/field as `deprecated: true`
- **API reference:** Add deprecation notice to endpoint documentation
- **Changelog:** Add entry to changelog with deprecation details
- **Deprecation register:** Update `contracts/deprecations/generated-contract-deprecations.json`

### 9.7 Ownership and Removal Date

Every deprecation must have:
- **Owner:** Team or individual responsible for the deprecation
- **Removal target:** Specific date when the deprecated feature will be removed
- **Tracking:** Issue or ticket tracking the removal

**Example:**
```json
{
  "key": "layer3-knowledge.json:POST /v1/query",
  "introduced_in": "v2.3",
  "removal_target": "v2.5",
  "replacement_endpoint": "POST /v1/query/graph",
  "owner": "platform-team",
  "removal_date": "2026-08-01"
}
```

### 9.8 Compatibility Shim Tracking

If a compatibility shim is used during deprecation (see Section 10), it must be tracked in the deprecation register with:
- Shim implementation location
- Shim expiration date
- Shim test coverage

## 10. Compatibility Shims

### 10.1 When Shims Are Allowed

Compatibility shims are allowed when:
- A breaking change is unavoidable but temporary
- The shim is a thin adapter layer (no complex logic)
- The shim has a clear removal target
- The shim is well-tested
- The shim is documented

**Example use cases:**
- Renaming a field while supporting the old name temporarily
- Supporting an old endpoint by proxying to a new endpoint
- Transforming old request formats to new formats

### 10.2 When Shims Are Not Allowed

Compatibility shims are not allowed when:
- The shim introduces complex business logic
- The shim has no clear removal target
- The shim is not tested
- The shim is not documented
- The shim weakens security or tenant isolation
- The shim introduces performance issues

### 10.3 How Shims Should Be Documented

Every shim must be documented with:
- **Purpose:** What the shim does and why it exists
- **Expiration:** When the shim will be removed
- **Removal plan:** How the shim will be removed
- **Test coverage:** How the shim is tested
- **Owner:** Who is responsible for the shim

**Example:**
```python
# COMPATIBILITY SHIM: Support old field name 'relationship_type'
# EXPIRATION: 2026-08-01 (aligned with v2.5 release)
# REMOVAL PLAN: Remove this field mapping and update OpenAPI spec
# TEST COVERAGE: tests/contract/test_l3_graph_contract.py::test_deprecated_relationship_type
# OWNER: platform-team

class GraphEdge(BaseModel):
    type: str  # new field name
    relationship_type: Optional[str] = None  # deprecated field name

    @validator('relationship_type', pre=True, always=True)
    def map_relationship_type_to_type(cls, v):
        if v is not None:
            # Log deprecation warning
            logger.warning("'relationship_type' is deprecated, use 'type' instead")
            return v
        return None
```

### 10.4 Expiration/Removal Target

Every shim must have a removal target:
- **Specific date:** When the shim will be removed
- **Version:** Which version will remove the shim
- **Tracking:** Issue or ticket tracking the removal

**Rule:** Shims should not live longer than 6 months unless explicitly approved.

### 10.5 Test Requirements for Shims

Every shim must be tested:
- **Unit tests:** Test the shim logic directly
- **Contract tests:** Test that the shim produces the expected output
- **Integration tests:** Test that the shim works end-to-end
- **Deprecation tests:** Test that deprecation warnings are emitted

### 10.6 Risk of Long-Lived Compatibility Layers

Long-lived compatibility layers introduce risks:
- **Technical debt:** Shims become permanent features
- **Confusion:** New developers may not understand why shims exist
- **Maintenance burden:** Shims must be maintained alongside new code
- **Performance overhead:** Shims add processing time
- **Security risk:** Shims may bypass security checks

**Rule:** Minimize shim lifetime. Remove shims as soon as possible.

## 11. Public vs Internal APIs

### 11.1 Public APIs Need Stricter Stability Guarantees

Public APIs (consumed by third parties, SDKs, or external systems) require:
- **Longer deprecation windows:** Minimum 6 months, recommended 12 months
- **Public announcements:** Blog posts, email notifications, social media
- **Detailed migration guides:** Step-by-step instructions with examples
- **Support during migration:** Help desk, documentation, Q&A
- **Multiple reminders:** Announcements at deprecation, mid-point, and near removal
- **Versioned contracts:** Clear versioning (e.g., `/api/v1`, `/api/v2`)

### 11.2 Internal APIs Still Require Contract Discipline

Internal APIs (consumed by frontend, agents, tests, other services) still require:
- **Contract stability:** Breaking changes still need deprecation and migration
- **Documentation:** Internal documentation of changes
- **Communication:** Internal announcements (Slack, email, team meetings)
- **Testing:** Contract tests to verify compatibility
- **Deprecation windows:** Minimum 3 months (shorter than public APIs)

**Internal does not mean informal.** Breaking internal contracts can still cause outages and failed workflows.

### 11.3 Breaking Internal Contracts Still Require Migration Planning

Even for internal APIs:
- Document the breaking change
- Provide a migration path
- Communicate with all internal consumers
- Update all internal consumers before removing old behavior
- Run contract tests to verify compatibility

**Example:**
```markdown
## Internal API Change: Layer 4 Workflow Status Response

**Breaking Change:** The `progress_percentage` field will change from 0-100 scale to 0.0-1.0 scale.

**Affected Consumers:**
- Frontend: `apps/web/src/features/workflows/hooks/useWorkflowStatus.ts`
- Agents: `services/layer4-agents/src/layer4_agents/tools/monitor_workflow.py`
- Tests: `tests/contract/test_l4_workflows_contract.py`

**Migration Plan:**
1. Update frontend to multiply by 100 for display
2. Update agents to use 0.0-1.0 scale
3. Update contract tests to expect 0.0-1.0 scale
4. Deploy changes to all consumers
5. Deploy backend change

**Timeline:**
- Announce: 2025-01-15
- Migration complete: 2025-02-01
- Backend change: 2025-02-15
```

## 12. Contract Testing Strategy

### 12.1 Build on Existing `tests/contract/` Infrastructure

The existing pytest contract tests in `tests/contract/` are the baseline. They verify:
- Request/response schema compliance
- Error envelope consistency
- Authentication and tenant context requirements
- Endpoint availability and behavior

**Do not replace these tests.** Extend them as needed.

### 12.2 OpenAPI Export Process

Every layer should export OpenAPI specs:
```bash
# Export OpenAPI for each layer
make contracts
```

This generates OpenAPI specs in `contracts/openapi/` for:
- `layer1-ingestion.json`
- `layer2-extraction.json`
- `layer3-knowledge.json`
- `layer4-agents.json`
- `layer5-ground-truth.json`
- `layer6-benchmarks.json`

### 12.3 Contract Tests for Request/Response Schemas

Verify that request/response schemas match OpenAPI:
```python
def test_workflow_create_request_schema():
    """Verify WorkflowCreateRequest matches OpenAPI spec."""
    spec = load_openapi_spec("contracts/openapi/layer4-agents.json")
    schema = spec["components"]["schemas"]["WorkflowCreateRequest"]
    
    # Validate schema structure
    assert "workflow_type" in schema["required"]
    assert "tenant_id" in schema["required"]
    assert "priority" in schema["properties"]
    assert schema["properties"]["priority"]["default"] == "NORMAL"
```

### 12.4 Contract Tests for Error Envelope Consistency

Verify that all errors follow the canonical error shape:
```python
def test_error_envelope_consistency():
    """Verify all errors follow the canonical error shape."""
    spec = load_openapi_spec("contracts/openapi/layer4-agents.json")
    
    for path, methods in spec["paths"].items():
        for method, details in methods.items():
            if "responses" in details:
                for status_code, response in details["responses"].items():
                    if status_code.startswith("4") or status_code.startswith("5"):
                        # Verify error envelope structure
                        assert "error" in response["content"]["application/json"]["schema"]
                        error_schema = response["content"]["application/json"]["schema"]["error"]
                        assert "code" in error_schema["required"]
                        assert "message" in error_schema["required"]
```

### 12.5 Contract Tests for Auth/Tenant Requirements

Verify that all endpoints require authentication and tenant context:
```python
def test_auth_tenant_requirements():
    """Verify all endpoints require auth and tenant context."""
    spec = load_openapi_spec("contracts/openapi/layer4-agents.json")
    
    for path, methods in spec["paths"].items():
        for method, details in methods.items():
            if path not in ["/health", "/ready"]:  # Exclude health endpoints
                # Verify auth requirement
                assert "security" in details
                assert any("BearerAuth" in s for s in details["security"])
                # Verify tenant context requirement
                assert "x-tenant-id" in details["parameters"]
```

### 12.6 Contract Tests for Deprecated Endpoints

Verify that deprecated endpoints emit deprecation headers:
```python
def test_deprecated_endpoint_headers():
    """Verify deprecated endpoints emit deprecation headers."""
    response = client.get("/v1/query")
    assert response.status_code == 200
    assert "Warning" in response.headers
    assert "X-Deprecated-Since" in response.headers
    assert "X-Target-Removal-Date" in response.headers
```

### 12.7 Contract Tests for Backward-Compatible Response Parsing

Verify that old clients can parse new responses:
```python
def test_backward_compatible_response_parsing():
    """Verify old clients can parse new responses with additional fields."""
    # Simulate old client that only knows about original fields
    old_client_fields = ["workflow_id", "status", "current_state"]
    
    response = client.get("/api/v1/workflows/{id}")
    response_data = response.json()
    
    # Old client should still be able to parse original fields
    for field in old_client_fields:
        assert field in response_data
```

### 12.8 Optional Future Tools

Future enhancements could include:

**openapi-diff:**
- Classify OpenAPI changes as breaking or non-breaking
- Generate deprecation notices automatically
- Integrate with CI to block breaking changes

```bash
# Example usage
openapi-diff contracts/openapi/layer4-agents.json \
  contracts/openapi/layer4-agents.json.previous \
  --fail-on-breaking
```

**Spectral:**
- Lint OpenAPI specs for best practices
- Enforce naming conventions
- Validate spec structure

```bash
# Example usage
spectral lint contracts/openapi/layer4-agents.json
```

**Generated Client Validation:**
- Auto-generate clients from OpenAPI
- Validate that generated clients build successfully
- Detect breaking changes in generated clients

**Consumer-Driven Contracts:**
- Use Pact or similar for consumer-driven contract testing
- Verify that backend meets consumer expectations
- Catch breaking changes before deployment

**Mock Server Validation:**
- Generate mock servers from OpenAPI
- Test clients against mock servers
- Verify client compatibility with contract changes

## 13. CI/CD Enforcement

### 13.1 OpenAPI Export Must Succeed

**Gate:** OpenAPI export must succeed before merge
```bash
# CI step
make contracts
```

**Failure:** Block merge if OpenAPI export fails

### 13.2 OpenAPI Schemas Must Be Valid

**Gate:** OpenAPI specs must be valid
```bash
# CI step
spectral lint contracts/openapi/*.json
```

**Failure:** Block merge if OpenAPI specs are invalid

### 13.3 Contract Tests Must Pass

**Gate:** Contract tests must pass
```bash
# CI step
pytest tests/contract/
```

**Failure:** Block merge if contract tests fail

### 13.4 Breaking OpenAPI Diffs Require Explicit Approval

**Gate:** Breaking OpenAPI changes require explicit approval
```bash
# CI step
openapi-diff contracts/openapi/layer4-agents.json \
  contracts/openapi/layer4-agents.json.base \
  --fail-on-breaking
```

**Failure:** Block merge if breaking changes are detected without approval

**Approval:** Require PR to reference an approved RFC issue (e.g., `Closes #123`)

### 13.5 Deprecated Endpoint Removals Require Migration Evidence

**Gate:** Removing deprecated endpoints requires migration evidence
```bash
# CI step
# Check if deprecated endpoint is being removed
# Verify that migration evidence is provided
```

**Failure:** Block merge if deprecated endpoint is removed without migration evidence

**Evidence:** Link to migration PR, issue, or documentation

### 13.6 Error Envelope Drift Blocks Merge

**Gate:** Error envelope changes are blocked
```bash
# CI step
# Compare error envelope schema against baseline
# Block changes to error envelope structure
```

**Failure:** Block merge if error envelope structure changes

**Exception:** Requires explicit approval and RFC

### 13.7 Tenant/Auth Contract Drift Blocks Merge

**Gate:** Authentication and tenant context changes are blocked
```bash
# CI step
# Compare auth/tenant requirements against baseline
# Block changes to auth/tenant behavior
```

**Failure:** Block merge if auth/tenant requirements change

**Exception:** Requires explicit approval and security review

### 13.8 Generated Clients Should Be Updated When Applicable

**Gate:** Generated clients should be updated when OpenAPI changes
```bash
# CI step
# Regenerate TypeScript clients
# Regenerate Python clients
# Verify clients build successfully
```

**Failure:** Warn if generated clients are not updated

**Block:** Block merge if generated clients fail to build

## 14. Reference Implementation Pattern

### 14.1 Export OpenAPI for Each Layer

```bash
# Export OpenAPI specs
make contracts

# This runs:
# - services/layer1-ingestion: export OpenAPI to contracts/openapi/layer1-ingestion.json
# - services/layer2-extraction: export OpenAPI to contracts/openapi/layer2-extraction.json
# - services/layer3-knowledge: export OpenAPI to contracts/openapi/layer3-knowledge.json
# - services/layer4-agents: export OpenAPI to contracts/openapi/layer4-agents.json
# - services/layer5-ground-truth: export OpenAPI to contracts/openapi/layer5-ground-truth.json
# - services/layer6-benchmarks: export OpenAPI to contracts/openapi/layer6-benchmarks.json
```

### 14.2 Compare Against Committed Baseline

```bash
# Compare OpenAPI specs against committed baseline
git diff contracts/openapi/layer4-agents.json

# Or use openapi-diff for automated comparison
openapi-diff contracts/openapi/layer4-agents.json \
  $(git show HEAD:contracts/openapi/layer4-agents.json) \
  --format markdown
```

### 14.3 Run Pytest Tests/Contract/

```bash
# Run contract tests
pytest tests/contract/

# Run specific contract test
pytest tests/contract/test_l4_workflows_contract.py
```

### 14.4 Fail CI on Unapproved Breaking Diffs

```yaml
# .github/workflows/contract-checks.yml
- name: Check for breaking OpenAPI changes
  run: |
    openapi-diff contracts/openapi/layer4-agents.json \
      $(git show HEAD:contracts/openapi/layer4-agents.json) \
      --fail-on-breaking
  # This step fails if breaking changes are detected
```

### 14.5 Allow Additive Diffs with Review

```yaml
# .github/workflows/contract-checks.yml
- name: Review additive OpenAPI changes
  run: |
    openapi-diff contracts/openapi/layer4-agents.json \
      $(git show HEAD:contracts/openapi/layer4-agents.json) \
      --format markdown > openapi-diff.md
    # Additive changes are allowed but require review
    echo "::notice::OpenAPI changes detected. Review openapi-diff.md"
```

### 14.6 Require Changelog Entry for Public or Consumer-Visible Changes

```yaml
# .github/workflows/contract-checks.yml
- name: Check for changelog entry
  run: |
    # Check if PR description references a changelog entry
    # or if CHANGELOG.md is updated
    if ! git diff --name-only | grep -q "CHANGELOG.md"; then
      echo "::error::Changelog entry required for public API changes"
      exit 1
    fi
```

## 15. API Change Checklist

Before merging any API change, complete this checklist:

### 15.1 Change Classification

- [ ] Is this change additive (new optional field, new endpoint)?
- [ ] Does this change remove or rename anything?
- [ ] Does this change change a field type?
- [ ] Does this change make an optional field required?
- [ ] Does this change remove enum values?
- [ ] Does this change change pagination shape?
- [ ] Does this change change error envelope shape?
- [ ] Does this change change auth or tenant context behavior?
- [ ] Does this change change response status codes?
- [ ] Does this change change semantic meaning of existing fields?

### 15.2 OpenAPI Updates

- [ ] Is OpenAPI spec updated for the affected layer?
- [ ] Are new fields documented with descriptions?
- [ ] Are deprecated fields marked with `deprecated: true`?
- [ ] Are deprecation headers documented in OpenAPI?
- [ ] Does OpenAPI spec pass linting (Spectral)?

### 15.3 Contract Test Updates

- [ ] Are contract tests updated for the change?
- [ ] Do contract tests pass?
- [ ] Are new endpoints covered by contract tests?
- [ ] Are deprecated endpoints still tested?
- [ ] Are error envelope tests updated?

### 15.4 Frontend/Generated Client Updates

- [ ] Are frontend hooks updated for the change?
- [ ] Are generated TypeScript clients updated?
- [ ] Are generated Python clients updated?
- [ ] Do generated clients build successfully?
- [ ] Is frontend type checking passing?

### 15.5 Migration Path

- [ ] Is a migration path documented?
- [ ] Is a deprecation notice needed?
- [ ] Is a compatibility shim needed?
- [ ] Is there a removal target date?
- [ ] Is the deprecation register updated?

### 15.6 Consumer Notification

- [ ] Have internal consumers been notified?
- [ ] Have public consumers been notified (if public API)?
- [ ] Is there a migration guide?
- [ ] Is there a changelog entry?
- [ ] Is there a blog post or announcement (if public API)?

### 15.7 Security and Tenant Isolation

- [ ] Does this change weaken security?
- [ ] Does this change weaken tenant isolation?
- [ ] Does this change bypass auth requirements?
- [ ] Does this change expose sensitive data?
- [ ] Is security review required?

## 16. Communication Templates

### 16.1 Internal API Change Notice

```markdown
Subject: [API Change] Layer 4 Workflow Status Response - Field Addition

**Layer:** Layer 4 (Agents)
**Endpoint:** GET /api/v1/workflows/{id}
**Change Type:** Additive (new optional field)
**Effective Date:** 2025-01-15

## Summary

We are adding a new optional field `estimated_completion_seconds` to the workflow status response. This field provides an estimate of when the workflow will complete.

## Impact

This is an additive change. Existing clients will continue to work without modification. New clients can use the new field if present.

## Migration

No migration required. Clients can optionally use the new field:

```python
response = client.get(f"/api/v1/workflows/{workflow_id}")
if "estimated_completion_seconds" in response.json():
    print(f"Estimated completion: {response.json()['estimated_completion_seconds']}s")
```

## Questions?

Contact: platform-team@example.com
```

### 16.2 Public API Deprecation Notice

```markdown
Subject: [Deprecation Notice] POST /v1/query - Removal on 2026-08-01

**API:** Layer 3 Knowledge Graph
**Endpoint:** POST /v1/query
**Deprecated Since:** 2026-04-14
**Removal Date:** 2026-08-01
**Replacement:** POST /v1/query/graph

## Summary

The `POST /v1/query` endpoint is deprecated and will be removed on 2026-08-01. Please migrate to the replacement endpoint `POST /v1/query/graph`.

## Migration Guide

Update your client code to use the new endpoint:

```python
# OLD (deprecated)
response = requests.post(
    "https://api.example.com/v1/query",
    headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    json={"query": "MATCH (n) RETURN n"}
)

# NEW (replacement)
response = requests.post(
    "https://api.example.com/v1/query/graph",
    headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant_id},
    json={"query": "MATCH (n) RETURN n"}
)
```

The new endpoint accepts the same request payload and returns the same response shape.

## Timeline

- **2026-04-14:** Deprecation announced
- **2026-06-01:** Reminder notice
- **2026-07-15:** Final reminder
- **2026-08-01:** Endpoint removed

## Support

If you need assistance with migration, contact api-support@example.com.

## Documentation

Full migration guide: https://docs.example.com/api/migrations/query-endpoint
```

### 16.3 Breaking Change Announcement

```markdown
Subject: [Breaking Change] Layer 3 Graph Node Schema - Field Rename

**Layer:** Layer 3 (Knowledge Graph)
**Endpoint:** GET /v1/value-trees, POST /v1/value-trees
**Change Type:** Breaking (field rename)
**Effective Date:** 2025-03-01
**API Version:** v2.0

## Summary

We are renaming the `label` field to `name` in the GraphNode schema. This is a breaking change that requires client updates.

## Breaking Change Details

The `label` field will be renamed to `name`:

```json
// BEFORE
{
  "id": "uuid",
  "label": "Operational Efficiency",
  "type": "value_driver"
}

// AFTER
{
  "id": "uuid",
  "name": "Operational Efficiency",  // was "label"
  "type": "value_driver"
}
```

## Migration Guide

Update your client code to use the new field name:

```python
# OLD
node_label = response.json()["label"]

# NEW
node_name = response.json()["name"]
```

## Compatibility Shim

A compatibility shim is in place to support the old `label` field until 2025-06-01. During this period, both `label` and `name` will be accepted in requests and returned in responses.

## Timeline

- **2025-02-01:** Announcement
- **2025-03-01:** Breaking change deployed (compatibility shim active)
- **2025-06-01:** Compatibility shim removed

## Support

If you need assistance with migration, contact platform-team@example.com.
```

### 16.4 Migration Reminder

```markdown
Subject: [Reminder] POST /v1/query Deprecation - Removal in 30 days

**API:** Layer 3 Knowledge Graph
**Endpoint:** POST /v1/query
**Removal Date:** 2026-08-01 (30 days from now)

## Reminder

This is a reminder that the `POST /v1/query` endpoint will be removed on 2026-08-01. Please migrate to the replacement endpoint `POST /v1/query/graph` before this date.

## Migration Guide

See the original deprecation notice for migration instructions: https://docs.example.com/api/migrations/query-endpoint

## Support

If you need assistance with migration, contact api-support@example.com.
```

### 16.5 Removal Completion Notice

```markdown
Subject: [Removal Complete] POST /v1/query - Removed on 2026-08-01

**API:** Layer 3 Knowledge Graph
**Endpoint:** POST /v1/query
**Removal Date:** 2026-08-01

## Summary

The `POST /v1/query` endpoint has been removed as scheduled. The replacement endpoint `POST /v1/query/graph` should be used instead.

## Action Required

If you have not yet migrated, please update your client code immediately to use the replacement endpoint.

## Documentation

Replacement endpoint documentation: https://docs.example.com/api/v1/query/graph
Migration guide: https://docs.example.com/api/migrations/query-endpoint

## Support

If you need assistance, contact api-support@example.com.
```

## 17. Examples

### 17.1 Safe Additive Field

**Change:** Add new optional field to response

```python
# BEFORE
class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str
    workflow_type: str
    status: str
    current_state: str
    progress_percentage: int

# AFTER (safe)
class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str
    workflow_type: str
    status: str
    current_state: str
    progress_percentage: int
    estimated_completion_seconds: Optional[int] = None  # new optional field
```

**OpenAPI:**
```yaml
estimated_completion_seconds:
  type: integer
  description: Estimated time until workflow completion in seconds
  nullable: true
```

**Impact:** Old clients ignore the new field. New clients can use it if present.

### 17.2 Unsafe Field Rename

**Change:** Rename field in response (breaking)

```python
# BEFORE
class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str
    status: str
    current_state: str

# AFTER (unsafe - breaking)
class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str
    status: str
    state: str  # renamed from "current_state"
```

**Correct approach:** Use compatibility shim:

```python
class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str
    status: str
    state: str  # new field name
    current_state: Optional[str] = None  # deprecated field name

    @validator('current_state', pre=True, always=True)
    def map_current_state_to_state(cls, v, values):
        if v is not None:
            logger.warning("'current_state' is deprecated, use 'state' instead")
            return v
        return values.get('state')
```

### 17.3 Endpoint Deprecation

**Change:** Deprecate endpoint before removal

```python
# OpenAPI
/v1/query:
  post:
    deprecated: true
    x-deprecated-since: "2026-04-14"
    x-removal-target: "2026-08-01"
    x-replacement-endpoint: "/v1/query/graph"
    description: |
      This endpoint is deprecated. Use POST /v1/query/graph instead.
      Will be removed on 2026-08-01.
```

**Implementation:**
```python
@router.post("/v1/query", deprecated=True)
async def query_graph(
    request: GraphQueryRequest,
    context: RequestContext = Depends(get_request_context)
):
    # Log deprecation warning
    logger.warning(
        "POST /v1/query is deprecated. Use POST /v1/query/graph instead. "
        "Will be removed on 2026-08-01."
    )
    # Implement endpoint
    return await query_service.execute(request.query)
```

### 17.4 Versioned Replacement Endpoint

**Change:** Create new versioned endpoint for breaking change

```python
# v1 (old)
@router.get("/api/v1/workflows/{id}")
async def get_workflow_v1(
    id: str,
    context: RequestContext = Depends(get_request_context)
):
    # Old implementation
    return {
        "workflow_id": id,
        "status": "running",
        "progress_percentage": 65  # 0-100 scale
    }

# v2 (new)
@router.get("/api/v2/workflows/{id}")
async def get_workflow_v2(
    id: str,
    context: RequestContext = Depends(get_request_context)
):
    # New implementation
    return {
        "workflow_id": id,
        "status": "running",
        "progress": 0.65  # 0.0-1.0 scale
    }
```

### 17.5 Compatibility Shim with Removal Target

**Change:** Support old field name temporarily

```python
# COMPATIBILITY SHIM: Support old field name 'relationship_type'
# EXPIRATION: 2026-08-01 (aligned with v2.5 release)
# REMOVAL PLAN: Remove this field mapping and update OpenAPI spec
# TEST COVERAGE: tests/contract/test_l3_graph_contract.py::test_deprecated_relationship_type
# OWNER: platform-team

class GraphEdge(BaseModel):
    type: str  # new field name
    relationship_type: Optional[str] = None  # deprecated field name

    @validator('relationship_type', pre=True, always=True)
    def map_relationship_type_to_type(cls, v):
        if v is not None:
            # Log deprecation warning
            logger.warning(
                "'relationship_type' is deprecated and will be removed on 2026-08-01. "
                "Use 'type' instead."
            )
            return v
        return None
```

### 17.6 Error Envelope Compatibility

**Change:** Add new optional field to error details

```json
// BEFORE
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": {
      "field_errors": {...}
    }
  }
}

// AFTER (safe)
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": {
      "field_errors": {...},
      "request_id": "uuid"  # new optional field
    }
  }
}
```

**Impact:** Old clients ignore the new field. New clients can use it for debugging.

### 17.7 Enum Evolution

**Change:** Add new enum value

```python
# BEFORE
class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# AFTER (safe - if clients tolerate unknown values)
class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"  # new value
```

**Client handling:**
```python
# Safe client handling (tolerates unknown values)
status = response.json()["status"]
if status in ["queued", "running", "completed", "failed"]:
    # Known status
    handle_known_status(status)
else:
    # Unknown status (e.g., "paused")
    handle_unknown_status(status)
```

## 18. Adjacent Contract Surfaces

### 18.1 Agent Tool Manifests

Agent tool manifests in `contracts/tool-manifests/` define the input/output contracts for agent skills. These are JSON Schema definitions that should eventually receive their own compatibility policy aligned with this document.

**Current state:** Tool manifests have version fields but no formal deprecation policy.

**Future work:** Define compatibility policy for tool manifests, including:
- Versioning strategy
- Breaking change criteria
- Deprecation process
- Migration guidance

### 18.2 Event/Message Contracts

If event or message contracts are added in the future (e.g., for async communication between layers), they should follow similar stability principles:
- Versioned schemas
- Backward compatibility
- Deprecation process
- Migration guidance

### 18.3 Generated SDKs

Generated SDKs (TypeScript, Python, etc.) are derived from OpenAPI specs. Their stability depends on OpenAPI spec stability. SDK versioning should follow semantic versioning principles:
- MAJOR: Breaking changes to SDK API
- MINOR: Additive changes
- PATCH: Bug fixes

### 18.4 Frontend API Clients

Frontend API clients in `apps/web/src/api/generated/` are auto-generated from OpenAPI specs. Their stability depends on:
- OpenAPI spec stability
- Type generation process
- Frontend build process

### 18.5 Workflow State Schemas

Workflow state schemas (e.g., LangGraph state definitions) are internal contracts between workflow nodes. These should also follow stability principles:
- Versioned state schemas
- Backward compatibility for state persistence
- Migration paths for state schema changes

**Future work:** Define compatibility policy for workflow state schemas.

## 19. Summary

Fabric_4L APIs are **stable by default**, **additive by preference**, **versioned when breaking**, **deprecated before removal**, and **protected by automated contract checks**. This document provides the practical implementation guide for achieving API contract stability across the 6-layer architecture. By following these principles, versioning policies, schema evolution rules, deprecation processes, and testing strategies, engineers can make API changes safely while minimizing disruption to consumers.

**Key takeaways:**
- Prefer additive changes over breaking changes
- Keep `/api/v1` stable unless breaking changes justify `/api/v2`
- Deprecate before removal with clear migration paths
- Automate contract checks in CI/CD
- Communicate changes early and clearly with consumers
- Never weaken security or tenant isolation for compatibility
- Use OpenAPI as the source of machine-readable truth
- Build on existing `tests/contract/` infrastructure

By adhering to these guidelines, Fabric_4L can maintain stable, reliable API contracts that support both current and future consumers.
