# Layer 5 Integration Contracts

This document defines the integration contracts between Layer 5 Ground Truth and other layers (Layer 4 Agents, Layer 6 Benchmarks).

## Overview

Layer 5 provides governance APIs for all governance entities (Formulas, Benchmarks, Policies, Assumptions, Value Realization Ledger, Approval Workflow). All cross-layer operations must go through these APIs to ensure proper governance, audit, and tenant isolation.

## Base URL

```
http://layer5-ground-truth:8005/api/v1/governance
```

## Authentication

All requests must include:
- `X-Tenant-ID`: Tenant UUID header
- `Authorization`: Bearer token with appropriate scopes
- `X-Service-Auth`: Service authentication header for inter-service calls

## Common Headers

```http
Content-Type: application/json
X-Tenant-ID: {tenant_uuid}
Authorization: Bearer {jwt_token}
X-Service-Auth: {service_auth_secret}
```

## Error Handling

All endpoints return standard error envelopes:

```json
{
  "detail": "Error message"
}
```

HTTP Status Codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `403`: Forbidden (permission denied)
- `404`: Not Found
- `409`: Conflict (slug conflict, version conflict)
- `422`: Unprocessable Entity (schema validation)
- `500`: Internal Server Error

---

## Formula Governance API

### Create Formula

Layer 4 agents use this to create new formulas for ROI calculations.

**Endpoint:** `POST /formulas`

**Required Scope:** `layer5.governance.formulas.create`

**Request:**
```json
{
  "name": "ROI Calculation",
  "slug": "roi-calculation",
  "formula_type": "roi",
  "expression": "revenue - costs",
  "expression_language": "python",
  "input_schema": {
    "type": "object",
    "properties": {
      "revenue": {"type": "number"},
      "costs": {"type": "number"}
    }
  },
  "output_schema": {
    "type": "number"
  },
  "parameters": [
    {
      "name": "discount_rate",
      "display_name": "Discount Rate",
      "parameter_type": "number",
      "required": true,
      "default_value": 0.1
    }
  ],
  "description": "Standard ROI calculation"
}
```

**Response:** `FormulaResponse` (201)

### Get Approved Formula

Layer 4 agents use this to retrieve approved formulas for calculations.

**Endpoint:** `GET /formulas/{formula_id}`

**Required Scope:** `layer5.governance.formulas.get`

**Response:** `FormulaResponse` (200)

### List Formulas

Layer 4 agents use this to discover available formulas.

**Endpoint:** `GET /formulas?page=1&page_size=50&formula_type=roi&is_active=true`

**Required Scope:** `layer5.governance.formulas.list`

**Response:** `PaginatedResponse` (200)

### Submit Formula for Approval

Layer 4 agents submit formula versions for approval.

**Endpoint:** `POST /formulas/{formula_id}/versions/{version}/submit`

**Required Scope:** `layer5.governance.formulas.submit`

**Response:** `FormulaVersionResponse` (200)

---

## Benchmark Governance API

### Create Benchmark

Layer 6 ingestion uses this to publish new benchmarks.

**Endpoint:** `POST /benchmarks`

**Required Scope:** `layer5.governance.benchmarks.create`

**Request:**
```json
{
  "name": "Industry ROI Average",
  "slug": "industry-roi-average",
  "benchmark_type": "industry_standard",
  "description": "Average ROI across industry",
  "source_name": "Industry Research Report",
  "source_url": "https://example.com/report",
  "source_type": "research",
  "source_date": "2024-01-01T00:00:00Z",
  "collection_methodology": "Survey of 500 companies",
  "confidence_level": "high",
  "sample_size": 500,
  "margin_of_error": {
    "lower": 0.15,
    "upper": 0.25
  },
  "data": {
    "values": [0.18, 0.20, 0.22, 0.19, 0.21],
    "mean": 0.20,
    "median": 0.20
  },
  "data_schema": {
    "type": "object",
    "properties": {
      "mean": {"type": "number"},
      "median": {"type": "number"}
    }
  },
  "effective_from": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

**Response:** `BenchmarkResponse` (201)

### Get Approved Benchmark

Layer 4 agents use this to retrieve approved benchmarks for comparison.

**Endpoint:** `GET /benchmarks/{benchmark_id}`

**Required Scope:** `layer5.governance.benchmarks.get`

**Response:** `BenchmarkResponse` (200)

### List Benchmarks

Layer 4 agents use this to discover available benchmarks.

**Endpoint:** `GET /benchmarks?page=1&page_size=50&benchmark_type=industry_standard&is_active=true`

**Required Scope:** `layer5.governance.benchmarks.list`

**Response:** `PaginatedResponse` (200)

---

## Policy Governance API

### Create Policy

Layer 4 agents use this to create validation policies.

**Endpoint:** `POST /policies`

**Required Scope:** `layer5.governance.policies.create`

**Request:**
```json
{
  "name": "ROI Validation Policy",
  "slug": "roi-validation-policy",
  "policy_type": "validation",
  "description": "Validates ROI calculations are within reasonable bounds",
  "rules": [
    {
      "rule_name": "roi_range_check",
      "rule_type": "validation",
      "condition": {"field": "roi", "operator": "between", "min": -1.0, "max": 10.0},
      "action": "reject",
      "severity": "high",
      "description": "ROI must be between -100% and 1000%"
    }
  ],
  "severity": "high",
  "scope": {
    "entity_types": ["formula", "value_entry"]
  }
}
```

**Response:** `PolicyResponse` (201)

### Evaluate Policy

Layer 4 agents use this to evaluate entities against policies.

**Endpoint:** `POST /policies/{policy_id}/evaluate`

**Required Scope:** `layer5.governance.policies.evaluate`

**Request:**
```json
{
  "entity_id": "uuid-of-entity",
  "entity_type": "formula",
  "context": {
    "roi": 0.25,
    "revenue": 1000000,
    "costs": 750000
  }
}
```

**Response:** `PolicyEvaluationResponse` (200)

---

## Assumption Governance API

### Create Assumption

Layer 4 agents use this to create assumptions for value calculations.

**Endpoint:** `POST /assumptions`

**Required Scope:** `layer5.governance.assumptions.create`

**Request:**
```json
{
  "name": "Market Growth Rate",
  "slug": "market-growth-rate",
  "assumption_type": "market_growth",
  "description": "Expected annual market growth",
  "value": 0.05,
  "value_type": "percentage",
  "impact_level": "high",
  "truth_object_id": "uuid-of-truth-object",
  "applies_to_opportunity_id": "uuid-of-opportunity"
}
```

**Response:** `AssumptionResponse` (201)

### Add Evidence to Assumption

Layer 4 agents use this to add supporting evidence.

**Endpoint:** `POST /assumptions/{assumption_id}/evidence`

**Required Scope:** `layer5.governance.assumptions.add_evidence`

**Request:**
```json
{
  "evidence_type": "research",
  "truth_object_id": "uuid-of-truth-object",
  "source_url": "https://example.com/study",
  "source_title": "Market Growth Study",
  "excerpt": "Market is expected to grow at 5% annually",
  "confidence": 0.85,
  "relevance": 0.9,
  "notes": "Primary source for market growth assumption"
}
```

**Response:** `AssumptionResponse` (201)

### Submit Assumption for Approval

Layer 4 agents submit high-impact assumptions for approval.

**Endpoint:** `POST /assumptions/{assumption_id}/submit`

**Required Scope:** `layer5.governance.assumptions.submit`

**Response:** `AssumptionResponse` (200)

---

## Value Realization Ledger API

### Create Value Entry

Layer 4 agents use this to record value realization entries.

**Endpoint:** `POST /value-entries`

**Required Scope:** `layer5.governance.value_entries.create`

**Request:**
```json
{
  "entry_type": "revenue",
  "entry_name": "Q1 2024 Revenue",
  "current_value": 1000000.0,
  "value_unit": "USD",
  "value_currency": "USD",
  "formula_id": "uuid-of-formula",
  "formula_version": "1.0.0",
  "assumption_ids": ["uuid-of-assumption"],
  "opportunity_id": "uuid-of-opportunity",
  "account_id": "uuid-of-account",
  "business_case_id": "uuid-of-business-case"
}
```

**Response:** `ValueRealizationEntryResponse` (201)

### Add Value Update

Layer 4 agents use this to record value changes (append-only).

**Endpoint:** `POST /value-entries/{entry_id}/updates`

**Required Scope:** `layer5.governance.value_entries.update`

**Request:**
```json
{
  "new_value": 1250000.0,
  "update_reason": "actual_q1_results",
  "update_notes": "Q1 exceeded projections by 25%",
  "formula_id_at_update": "uuid-of-formula",
  "formula_version_at_update": "1.0.0",
  "calculation_metadata": {
    "input_values": {"revenue": 1250000, "costs": 750000}
  }
}
```

**Response:** `ValueRealizationEntryResponse` (201)

---

## Approval Workflow API

### List Pending Approvals

Layer 4 agents use this to check pending approval status.

**Endpoint:** `GET /approvals?status=pending&entity_type=formula&page=1&page_size=50`

**Required Scope:** `layer5.governance.approvals.list`

**Response:** `PaginatedResponse` (200)

### Get Approval Request

Layer 4 agents use this to get approval request details.

**Endpoint:** `GET /approvals/{approval_id}`

**Required Scope:** `layer5.governance.approvals.get`

**Response:** `ApprovalRequestResponse` (200)

### Approve Request

Layer 4 agents with approval permissions use this to approve requests.

**Endpoint:** `POST /approvals/{approval_id}/approve`

**Required Scope:** `layer5.governance.approvals.approve`

**Request:**
```json
{
  "notes": "Formula validated and approved for use"
}
```

**Response:** `ApprovalRequestResponse` (200)

### Reject Request

Layer 4 agents with approval permissions use this to reject requests.

**Endpoint:** `POST /approvals/{approval_id}/reject`

**Required Scope:** `layer5.governance.approvals.reject`

**Request:**
```json
{
  "notes": "Formula expression contains errors"
}
```

**Response:** `ApprovalRequestResponse` (200)

---

## Integration Patterns

### Pattern 1: Layer 4 Agent Formula Usage

1. **Discovery:** Agent lists available formulas via `GET /formulas`
2. **Retrieval:** Agent gets approved formula via `GET /formulas/{id}`
3. **Calculation:** Agent uses formula expression for calculations
4. **Validation:** Agent evaluates result against policies via `POST /policies/{id}/evaluate`
5. **Recording:** Agent records value entry via `POST /value-entries`

### Pattern 2: Layer 6 Benchmark Ingestion

1. **Ingestion:** Layer 6 receives benchmark data from external source
2. **Validation:** Layer 6 validates data structure
3. **Creation:** Layer 6 creates benchmark via `POST /benchmarks`
4. **Approval:** Layer 6 submits for approval via `POST /benchmarks/{id}/versions/{version}/submit`
5. **Publication:** Once approved, benchmark is available to Layer 4 agents

### Pattern 3: Layer 4 Assumption Management

1. **Creation:** Agent creates assumption via `POST /assumptions`
2. **Evidence:** Agent adds evidence via `POST /assumptions/{id}/evidence`
3. **Approval:** High-impact assumptions submitted via `POST /assumptions/{id}/submit`
4. **Usage:** Approved assumptions used in calculations
5. **Validation:** Assumptions validated against policies

---

## Rate Limits

All Layer 5 APIs are rate-limited per tenant:
- Read operations: 1000 requests/minute
- Write operations: 100 requests/minute
- Approval operations: 50 requests/minute

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset time (Unix timestamp)

---

## Versioning

API version: `v1`

Breaking changes will increment the major version. Non-breaking changes (new fields, new endpoints) will not change the version.

---

## Support

For integration issues, contact the Layer 5 team or refer to the governance documentation.
