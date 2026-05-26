# Layer 5 Governance API Reference

Complete API reference for Layer 5 Ground Truth governance operations.

## Base URL

```
http://layer5-ground-truth:8005/api/v1/governance
```

## Authentication

All requests require:
- `X-Tenant-ID`: Tenant UUID header
- `Authorization`: Bearer JWT token with appropriate scopes
- `X-Service-Auth`: Service authentication for inter-service calls

## Response Formats

### Success Response

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Error Response

```json
{
  "detail": "Error message"
}
```

### Paginated Response

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 50,
  "has_next": true
}
```

---

## Formula Governance

### Create Formula

Create a new formula in DRAFT status.

**Endpoint:** `POST /formulas`

**Required Scope:** `layer5.governance.formulas.create`

**Request Body:**
```json
{
  "name": "string (required)",
  "slug": "string (required, unique per tenant)",
  "formula_type": "string (required, enum: roi, npv, irr, custom)",
  "expression": "string (required)",
  "expression_language": "string (required, enum: python, javascript, sql)",
  "input_schema": "object (required, JSON Schema)",
  "output_schema": "object (required, JSON Schema)",
  "parameters": [
    {
      "name": "string (required)",
      "display_name": "string (required)",
      "parameter_type": "string (required, enum: number, string, boolean, array, object)",
      "required": "boolean (required)",
      "default_value": "any (optional)",
      "description": "string (optional)"
    }
  ],
  "description": "string (optional)"
}
```

**Response:** `FormulaResponse` (201)

**Status Codes:**
- `201`: Formula created
- `409`: Slug conflict
- `422`: Validation error

### List Formulas

List formulas with pagination and filtering.

**Endpoint:** `GET /formulas`

**Required Scope:** `layer5.governance.formulas.list`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)
- `formula_type`: string (optional filter)
- `is_active`: boolean (optional filter)
- `status`: string (optional filter: DRAFT, PENDING_APPROVAL, APPROVED, DEPRECATED)

**Response:** `PaginatedResponse<FormulaResponse>` (200)

### Get Formula

Get a formula by ID.

**Endpoint:** `GET /formulas/{formula_id}`

**Required Scope:** `layer5.governance.formulas.get`

**Response:** `FormulaResponse` (200)

**Status Codes:**
- `404`: Formula not found

### Create Formula Version

Create a new version of a formula.

**Endpoint:** `POST /formulas/{formula_id}/versions`

**Required Scope:** `layer5.governance.formulas.create_version`

**Request Body:**
```json
{
  "version": "string (required, semver format)",
  "expression": "string (required)",
  "expression_language": "string (required)",
  "change_description": "string (required)"
}
```

**Response:** `FormulaVersionResponse` (201)

### Submit Formula for Approval

Submit a formula version for approval.

**Endpoint:** `POST /formulas/{formula_id}/versions/{version}/submit`

**Required Scope:** `layer5.governance.formulas.submit`

**Response:** `FormulaVersionResponse` (200)

### Approve Formula Version

Approve a formula version.

**Endpoint:** `POST /formulas/{formula_id}/versions/{version}/approve`

**Required Scope:** `layer5.governance.formulas.approve`

**Response:** `FormulaVersionResponse` (200)

### Reject Formula Version

Reject a formula version.

**Endpoint:** `POST /formulas/{formula_id}/versions/{version}/reject`

**Required Scope:** `layer5.governance.formulas.reject`

**Request Body:**
```json
{
  "reason": "string (required)"
}
```

**Response:** `FormulaVersionResponse` (200)

### Deprecate Formula

Deprecate a formula.

**Endpoint:** `POST /formulas/{formula_id}/deprecate`

**Required Scope:** `layer5.governance.formulas.deprecate`

**Query Parameters:**
- `reason`: string (required)

**Response:** `FormulaResponse` (200)

### Archive Formula

Archive a formula.

**Endpoint:** `POST /formulas/{formula_id}/archive`

**Required Scope:** `layer5.governance.formulas.archive`

**Response:** `FormulaResponse` (200)

---

## Benchmark Governance

### Create Benchmark

Create a new benchmark.

**Endpoint:** `POST /benchmarks`

**Required Scope:** `layer5.governance.benchmarks.create`

**Request Body:**
```json
{
  "name": "string (required)",
  "slug": "string (required, unique per tenant)",
  "benchmark_type": "string (required, enum: industry_standard, internal, competitive)",
  "description": "string (optional)",
  "source_name": "string (required)",
  "source_url": "string (optional)",
  "source_type": "string (required, enum: research, survey, internal, external)",
  "source_date": "string (optional, ISO 8601)",
  "collection_methodology": "string (optional)",
  "confidence_level": "string (optional, enum: low, medium, high)",
  "sample_size": "integer (optional)",
  "margin_of_error": {
    "lower": "number (optional)",
    "upper": "number (optional)"
  },
  "data": "object (required)",
  "data_schema": "object (required, JSON Schema)",
  "effective_from": "string (required, ISO 8601)",
  "version": "string (optional, semver format)"
}
```

**Response:** `BenchmarkResponse` (201)

### List Benchmarks

List benchmarks with pagination and filtering.

**Endpoint:** `GET /benchmarks`

**Required Scope:** `layer5.governance.benchmarks.list`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)
- `benchmark_type`: string (optional filter)
- `is_active`: boolean (optional filter)

**Response:** `PaginatedResponse<BenchmarkResponse>` (200)

### Get Benchmark

Get a benchmark by ID.

**Endpoint:** `GET /benchmarks/{benchmark_id}`

**Required Scope:** `layer5.governance.benchmarks.get`

**Response:** `BenchmarkResponse` (200)

### Create Benchmark Version

Create a new version of a benchmark.

**Endpoint:** `POST /benchmarks/{benchmark_id}/versions`

**Required Scope:** `layer5.governance.benchmarks.create_version`

**Request Body:**
```json
{
  "version": "string (required, semver format)",
  "data": "object (required)",
  "change_description": "string (required)",
  "effective_from": "string (required, ISO 8601)"
}
```

**Response:** `BenchmarkVersionResponse` (201)

### Approve Benchmark Version

Approve a benchmark version.

**Endpoint:** `POST /benchmarks/{benchmark_id}/versions/{version}/approve`

**Required Scope:** `layer5.governance.benchmarks.approve`

**Response:** `BenchmarkVersionResponse` (200)

### Deprecate Benchmark

Deprecate a benchmark.

**Endpoint:** `POST /benchmarks/{benchmark_id}/deprecate`

**Required Scope:** `layer5.governance.benchmarks.deprecate`

**Query Parameters:**
- `reason`: string (required)

**Response:** `BenchmarkResponse` (200)

---

## Policy Governance

### Create Policy

Create a new policy.

**Endpoint:** `POST /policies`

**Required Scope:** `layer5.governance.policies.create`

**Request Body:**
```json
{
  "name": "string (required)",
  "slug": "string (required, unique per tenant)",
  "policy_type": "string (required, enum: validation, compliance, governance)",
  "description": "string (optional)",
  "rules": [
    {
      "rule_name": "string (required)",
      "rule_type": "string (required, enum: validation, compliance, governance)",
      "condition": "object (required)",
      "action": "string (required, enum: approve, reject, warn, notify)",
      "severity": "string (required, enum: low, medium, high, critical)",
      "description": "string (optional)"
    }
  ],
  "severity": "string (required, enum: low, medium, high, critical)",
  "scope": {
    "entity_types": ["string (optional)"]
  }
}
```

**Response:** `PolicyResponse` (201)

### List Policies

List policies with pagination and filtering.

**Endpoint:** `GET /policies`

**Required Scope:** `layer5.governance.policies.list`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)
- `policy_type`: string (optional filter)
- `is_active`: boolean (optional filter)

**Response:** `PaginatedResponse<PolicyResponse>` (200)

### Get Policy

Get a policy by ID.

**Endpoint:** `GET /policies/{policy_id}`

**Required Scope:** `layer5.governance.policies.get`

**Response:** `PolicyResponse` (200)

### Evaluate Policy

Evaluate an entity against a policy.

**Endpoint:** `POST /policies/{policy_id}/evaluate`

**Required Scope:** `layer5.governance.policies.evaluate`

**Request Body:**
```json
{
  "entity_id": "string (required, UUID)",
  "entity_type": "string (required)",
  "context": "object (optional)"
}
```

**Response:** `PolicyEvaluationResponse` (200)

### Get Policy History

Get evaluation history for a policy.

**Endpoint:** `GET /policies/{policy_id}/history`

**Required Scope:** `layer5.governance.policies.get_history`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)

**Response:** `PaginatedResponse<PolicyEvaluationResponse>` (200)

---

## Assumption Governance

### Create Assumption

Create a new assumption.

**Endpoint:** `POST /assumptions`

**Required Scope:** `layer5.governance.assumptions.create`

**Request Body:**
```json
{
  "name": "string (required)",
  "slug": "string (required, unique per tenant)",
  "assumption_type": "string (required, enum: market_growth, cost_reduction, efficiency_gain, risk_factor, custom)",
  "description": "string (optional)",
  "value": "number (required)",
  "value_type": "string (required, enum: number, percentage, currency, boolean)",
  "impact_level": "string (required, enum: low, medium, high, critical)",
  "truth_object_id": "string (optional, UUID)",
  "applies_to_opportunity_id": "string (optional, UUID)",
  "applies_to_formula_id": "string (optional, UUID)"
}
```

**Response:** `AssumptionResponse` (201)

### List Assumptions

List assumptions with pagination and filtering.

**Endpoint:** `GET /assumptions`

**Required Scope:** `layer5.governance.assumptions.list`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)
- `assumption_type`: string (optional filter)
- `impact_level`: string (optional filter)
- `status`: string (optional filter)

**Response:** `PaginatedResponse<AssumptionResponse>` (200)

### Get Assumption

Get an assumption by ID.

**Endpoint:** `GET /assumptions/{assumption_id}`

**Required Scope:** `layer5.governance.assumptions.get`

**Response:** `AssumptionResponse` (200)

### Add Evidence to Assumption

Add supporting evidence to an assumption.

**Endpoint:** `POST /assumptions/{assumption_id}/evidence`

**Required Scope:** `layer5.governance.assumptions.add_evidence`

**Request Body:**
```json
{
  "evidence_type": "string (required, enum: research, data, expert_opinion, internal, external)",
  "truth_object_id": "string (optional, UUID)",
  "source_url": "string (optional)",
  "source_title": "string (optional)",
  "excerpt": "string (optional)",
  "confidence": "number (optional, 0-1)",
  "relevance": "number (optional, 0-1)",
  "notes": "string (optional)"
}
```

**Response:** `AssumptionResponse` (201)

### Submit Assumption for Approval

Submit an assumption for approval.

**Endpoint:** `POST /assumptions/{assumption_id}/submit`

**Required Scope:** `layer5.governance.assumptions.submit`

**Response:** `AssumptionResponse` (200)

---

## Value Realization Ledger

### Create Value Entry

Create a new value realization entry.

**Endpoint:** `POST /value-entries`

**Required Scope:** `layer5.governance.value_entries.create`

**Request Body:**
```json
{
  "entry_type": "string (required, enum: revenue, cost, efficiency, risk, custom)",
  "entry_name": "string (required)",
  "current_value": "number (required)",
  "description": "string (optional)",
  "value_unit": "string (optional)",
  "value_currency": "string (optional)",
  "formula_id": "string (optional, UUID)",
  "formula_version": "string (optional)",
  "benchmark_id": "string (optional, UUID)",
  "benchmark_version": "string (optional)",
  "assumption_ids": ["string (optional, UUID array)"],
  "opportunity_id": "string (optional, UUID)",
  "account_id": "string (optional, UUID)",
  "business_case_id": "string (optional, UUID)"
}
```

**Response:** `ValueRealizationEntryResponse` (201)

### List Value Entries

List value entries with pagination and filtering.

**Endpoint:** `GET /value-entries`

**Required Scope:** `layer5.governance.value_entries.list`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)
- `entry_type`: string (optional filter)
- `opportunity_id`: string (optional filter, UUID)
- `account_id`: string (optional filter, UUID)

**Response:** `PaginatedResponse<ValueRealizationEntryResponse>` (200)

### Get Value Entry

Get a value entry by ID.

**Endpoint:** `GET /value-entries/{entry_id}`

**Required Scope:** `layer5.governance.value_entries.get`

**Response:** `ValueRealizationEntryResponse` (200)

### Add Value Update

Add an update to a value entry (append-only).

**Endpoint:** `POST /value-entries/{entry_id}/updates`

**Required Scope:** `layer5.governance.value_entries.update`

**Request Body:**
```json
{
  "new_value": "number (required)",
  "update_reason": "string (required, enum: actual_results, recalculation, correction, adjustment)",
  "update_notes": "string (optional)",
  "formula_id_at_update": "string (optional, UUID)",
  "formula_version_at_update": "string (optional)",
  "benchmark_id_at_update": "string (optional, UUID)",
  "benchmark_version_at_update": "string (optional)",
  "assumption_ids_at_update": ["string (optional, UUID array)"],
  "calculation_metadata": "object (optional)"
}
```

**Response:** `ValueRealizationEntryResponse` (201)

### Get Value Updates

Get update history for a value entry.

**Endpoint:** `GET /value-entries/{entry_id}/updates`

**Required Scope:** `layer5.governance.value_entries.get_updates`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)

**Response:** `PaginatedResponse<ValueRealizationUpdateResponse>` (200)

---

## Approval Workflow

### List Approval Requests

List approval requests with pagination and filtering.

**Endpoint:** `GET /approvals`

**Required Scope:** `layer5.governance.approvals.list`

**Query Parameters:**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50, max: 100)
- `entity_type`: string (optional filter)
- `status`: string (optional filter: PENDING, APPROVED, REJECTED)

**Response:** `PaginatedResponse<ApprovalRequestResponse>` (200)

### Get Approval Request

Get an approval request by ID.

**Endpoint:** `GET /approvals/{approval_id}`

**Required Scope:** `layer5.governance.approvals.get`

**Response:** `ApprovalRequestResponse` (200)

### Approve Request

Approve a pending approval request.

**Endpoint:** `POST /approvals/{approval_id}/approve`

**Required Scope:** `layer5.governance.approvals.approve`

**Request Body:**
```json
{
  "notes": "string (optional)"
}
```

**Response:** `ApprovalRequestResponse` (200)

### Reject Request

Reject a pending approval request.

**Endpoint:** `POST /approvals/{approval_id}/reject`

**Required Scope:** `layer5.governance.approvals.reject`

**Request Body:**
```json
{
  "notes": "string (optional)"
}
```

**Response:** `ApprovalRequestResponse` (200)

---

## Metrics

### Get Governance Metrics

Get Prometheus metrics for governance operations.

**Endpoint:** `GET /metrics`

**Required Scope:** None (internal endpoint)

**Response:** Prometheus text format (200)

---

## Data Models

### FormulaResponse

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "slug": "string",
  "formula_type": "string",
  "description": "string",
  "current_version": "string",
  "latest_version": "string",
  "input_schema": "object",
  "output_schema": "object",
  "is_active": "boolean",
  "deprecated_at": "string (ISO 8601)",
  "deprecation_reason": "string",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### BenchmarkResponse

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "slug": "string",
  "benchmark_type": "string",
  "description": "string",
  "source_name": "string",
  "source_url": "string",
  "source_type": "string",
  "current_version": "string",
  "latest_version": "string",
  "data": "object",
  "data_schema": "object",
  "effective_from": "string (ISO 8601)",
  "is_active": "boolean",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### PolicyResponse

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "slug": "string",
  "policy_type": "string",
  "description": "string",
  "rules": ["array"],
  "severity": "string",
  "is_active": "boolean",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### AssumptionResponse

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "slug": "string",
  "assumption_type": "string",
  "description": "string",
  "value": "number",
  "value_type": "string",
  "impact_level": "string",
  "sensitivity_analysis": "object",
  "truth_object_id": "uuid",
  "evidence_count": "integer",
  "status": "string",
  "is_active": "boolean",
  "approval_request_id": "uuid",
  "approved_by": "string",
  "approved_at": "string (ISO 8601)",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### ValueRealizationEntryResponse

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "entry_type": "string",
  "entry_name": "string",
  "description": "string",
  "current_value": "number",
  "value_unit": "string",
  "value_currency": "string",
  "formula_id": "uuid",
  "formula_version": "string",
  "benchmark_id": "uuid",
  "benchmark_version": "string",
  "assumption_ids": ["uuid array"],
  "opportunity_id": "uuid",
  "account_id": "uuid",
  "business_case_id": "uuid",
  "is_active": "boolean",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```

### ApprovalRequestResponse

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "entity_type": "string",
  "entity_id": "uuid",
  "entity_version": "string",
  "status": "string",
  "requested_by": "string",
  "requested_at": "string (ISO 8601)",
  "request_reason": "string",
  "request_metadata": "object",
  "reviewed_by": "string",
  "reviewed_at": "string (ISO 8601)",
  "review_notes": "string",
  "approved_at": "string (ISO 8601)",
  "rejected_at": "string (ISO 8601)",
  "created_at": "string (ISO 8601)",
  "updated_at": "string (ISO 8601)"
}
```
