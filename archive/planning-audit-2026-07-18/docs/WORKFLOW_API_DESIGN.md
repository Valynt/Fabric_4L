# Workflow API Design

**Date:** 2026-05-06  
**Status:** Design Phase  
**Priority:** Production readiness

## Overview

Design for missing API endpoints required to replace mock data in workflow pages.

## 1. Stakeholder Mapping API

### Purpose
Identify and analyze key stakeholders for a prospect account using CRM data and company information.

### Endpoint
```
GET /v1/intelligence/account/{accountId}/stakeholders
```

### Response Schema
```typescript
interface Stakeholder {
  id: string;
  name: string;
  title: string;
  role: "Champion" | "Decision Maker" | "Influencer" | "Approver" | "User";
  influence: number; // 0-100
  interest: number; // 0-100
  concern: string;
  source: string; // CRM, LinkedIn, etc.
}

interface StakeholderResponse {
  account_id: string;
  stakeholders: Stakeholder[];
  generated_at: string;
}
```

### Implementation Location
**Service:** Layer 4 Agents  
**Route:** `src/api/routes/intelligence.py`  
**Tool:** `analyze_stakeholders` (new tool in tools/)

### Implementation Approach
1. Use existing CRM integration tools to fetch contact data
2. Apply AI analysis to determine roles, influence, and interest
3. Use LangGraph workflow to analyze relationships and concerns

---

## 2. Ontology/Capability Matching API

### Purpose
Match product capabilities from ontology to detected pain signals.

### Endpoint
```
GET /v1/intelligence/account/{accountId}/capability-matches
```

### Response Schema
```typescript
interface CapabilityMatch {
  capability_id: string;
  capability_name: string;
  relevance_score: number; // 0-100
  matched_pain_signal: string;
  evidence_count: number;
  confidence: number; // 0-100
}

interface CapabilityMatchResponse {
  account_id: string;
  matches: CapabilityMatch[];
  generated_at: string;
}
```

### Implementation Location
**Service:** Layer 3 Knowledge  
**Route:** `src/api/routes/ontology.py` (or extend existing routes)  
**Query:** Neo4j Cypher query to match capabilities to pain signals

### Implementation Approach
1. Query Neo4j for product capabilities in ontology
2. Match against pain signals using semantic similarity
3. Return ranked matches with evidence counts

---

## 3. Value Lever Configuration API

### Purpose
Provide configuration for value calculation levers (base values, ranges, units).

### Endpoint
```
GET /v1/calculators/levers
```

### Request Parameters
```typescript
interface LeverConfigRequest {
  industry?: string;
  company_size?: string;
  product_line?: string;
}
```

### Response Schema
```typescript
interface ValueLever {
  id: string;
  name: string;
  base_value: number;
  min_value: number;
  max_value: number;
  unit: string;
  annual_impact: number;
  confidence: number; // 0-100
  category: string;
}

interface LeverConfigResponse {
  levers: ValueLever[];
  metadata: {
    industry: string;
    company_size: string;
    version: string;
  };
}
```

### Implementation Location
**Service:** Layer 3 Knowledge  
**Route:** `src/api/routes/calculators.py` (new route file)  
**Storage:** Neo4j nodes with label `ValueLever`

### Implementation Approach
1. Store lever configurations in Neo4j as nodes
2. Filter by industry/company size if provided
3. Return tenant-scoped results

---

## 4. Value Case Persistence API

### Purpose
Save and retrieve generated value cases with scenarios and calculations.

### Endpoints
```
POST /v1/calculators/value-cases
GET /v1/calculators/value-cases/{caseId}
PUT /v1/calculators/value-cases/{caseId}
```

### Request Schema (POST/PUT)
```typescript
interface ValueCaseRequest {
  account_id: string;
  prospect_id?: string;
  levers: {
    lever_id: string;
    scenario_a: number;
    scenario_b: number;
    scenario_c?: number;
  }[];
  scenarios: {
    name: "Conservative" | "Expected" | "Optimistic";
    total_value: number;
    breakdown: {
      area: string;
      value: number;
      percentage: number;
    }[];
  }[];
  metadata: {
    generated_by: string;
    confidence_score: number;
  };
}
```

### Response Schema
```typescript
interface ValueCaseResponse {
  case_id: string;
  account_id: string;
  created_at: string;
  updated_at: string;
  levers: ValueCaseRequest['levers'];
  scenarios: ValueCaseRequest['scenarios'];
  metadata: ValueCaseRequest['metadata'];
}
```

### Implementation Location
**Service:** Layer 3 Knowledge  
**Route:** `src/api/routes/calculators.py`  
**Storage:** Neo4j nodes with label `ValueCase`

### Implementation Approach
1. Store value cases in Neo4j with tenant isolation
2. Link to account and prospect entities
3. Support versioning for updates

---

## Implementation Priority

Given the 1-day production deadline, prioritize:

1. **Value Lever Configuration API** (Layer 3) - Pure data, no AI required
2. **Value Case Persistence API** (Layer 3) - CRUD operations, straightforward
3. **Ontology/Capability Matching API** (Layer 3) - Query-based, no AI required
4. **Stakeholder Mapping API** (Layer 4) - Requires AI workflow, most complex

## Frontend Hook Creation

After implementing APIs, create corresponding hooks:

1. `useStakeholders(accountId)` - calls stakeholder API
2. `useCapabilityMatches(accountId)` - calls ontology matching API
3. `useValueLeverConfig(filters)` - calls lever config API
4. `useValueCases()` - CRUD hooks for value cases
