# Layer 4 Pagination Contract — Frontend Requirements

**Status**: Backend Contract Gap Identified
**Date**: 2026-04-11
**Priority**: P2 (Medium) — Not blocking current functionality

---

## Current State

The frontend currently uses `GET /api/v1/agents/workflows/active` to fetch workflow data for both:
1. **Active workflows panel** (`useActiveWorkflows` hook)
2. **Workflow history** (`useWorkflowHistory` hook) — uses same endpoint as temporary proxy

### Current Endpoint
```
GET /api/v1/agents/workflows/active
```

**Response**: Array of workflow objects (no pagination metadata)
```json
[
  {
    "workflow_id": "wf-1",
    "workflow_type": "market_analysis",
    "status": "running",
    "progress_percentage": 65,
    "created_at": "2024-01-15T10:00:00Z"
  }
]
```

**Issues**:
- Returns ALL workflows for tenant (unbounded result set)
- No pagination controls available
- No sorting options
- No filtering beyond tenant_id
- Frontend must load entire dataset for history view

---

## Required Contract

### New Endpoint
```
GET /api/v1/workflows
```

### Query Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `status` | string | No | Filter by workflow status | `active`, `completed`, `failed`, `cancelled`, `all` |
| `type` | string | No | Filter by workflow type | `roi_calculator`, `whitespace_analysis`, `business_case` |
| `limit` | integer | No | Number of items to return (default: 20, max: 100) | `20` |
| `offset` | integer | No | Number of items to skip for pagination | `0`, `20`, `40` |
| `sort_by` | string | No | Field to sort by | `created_at`, `updated_at`, `status`, `progress_percentage` |
| `sort_order` | string | No | Sort direction | `asc`, `desc` |
| `search` | string | No | Text search across workflow name/type | `analysis` |

### Request Example
```
GET /api/v1/workflows?status=completed&limit=20&offset=0&sort_by=created_at&sort_order=desc
```

### Response Format
```json
{
  "items": [
    {
      "workflow_instance_id": "wf-123",
      "workflow_type": "business_case",
      "status": "completed",
      "progress_percentage": 100,
      "created_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T10:30:00Z",
      "created_by": "user@example.com"
    }
  ],
  "pagination": {
    "total": 156,
    "limit": 20,
    "offset": 0,
    "has_more": true,
    "total_pages": 8,
    "current_page": 1
  },
  "meta": {
    "request_id": "req-uuid",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

### Response Fields

**Item Fields** (same as current workflow object, but consistent naming):
| Field | Type | Description |
|-------|------|-------------|
| `workflow_instance_id` | string | Unique workflow identifier |
| `workflow_type` | string | Type of workflow |
| `status` | string | Current status |
| `progress_percentage` | number | 0-100 completion percentage |
| `created_at` | ISO timestamp | Creation time |
| `updated_at` | ISO timestamp | Last update time |
| `completed_at` | ISO timestamp | Completion time (null if not complete) |
| `created_by` | string | User who created workflow |

**Pagination Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `total` | integer | Total number of items matching query |
| `limit` | integer | Items per page (echoed from request) |
| `offset` | integer | Current offset (echoed from request) |
| `has_more` | boolean | Whether more items exist beyond current page |
| `total_pages` | integer | Total number of pages |
| `current_page` | integer | Current page number (1-indexed) |

---

## Frontend Implementation Plan

Once backend supports pagination, the frontend will update:

### 1. Update `useWorkflowHistory` Hook
```typescript
export function useWorkflowHistory(filters: {
  status?: 'active' | 'completed' | 'failed' | 'all';
  limit?: number;
  offset?: number;
  sortBy?: 'created_at' | 'updated_at';
} = {}) {
  const { status = 'all', limit = 20, offset = 0, sortBy = 'created_at' } = filters;

  return useQuery({
    queryKey: WORKFLOW_KEYS.history({ status, limit, offset, sortBy }),
    queryFn: async () => {
      const response = await apiClient.get('l4', '/workflows', {
        params: { status, limit, offset, sort_by: sortBy }
      });
      return {
        workflows: normalizeWorkflowList(response.data.items),
        pagination: response.data.pagination
      };
    },
    staleTime: 60 * 1000,
  });
}
```

### 2. Add Pagination UI Component
- Previous/Next buttons
- Page number indicator
- Items per page selector (20, 50, 100)
- "Showing X to Y of Z results" text

### 3. Update Query Keys for Pagination
```typescript
const WORKFLOW_KEYS = {
  history: (filters: { status: string; limit: number; offset: number; sortBy: string }) =>
    [...WORKFLOW_KEYS.all, 'history', filters] as const,
};
```

---

## Migration Path

### Phase 1: Backend Implementation
1. Create new `GET /api/v1/workflows` endpoint with pagination
2. Keep existing `GET /api/v1/agents/workflows/active` for backward compatibility
3. Add deprecation notice to old endpoint

### Phase 2: Frontend Migration
1. Update `useWorkflowHistory` to use new endpoint
2. Add pagination UI
3. Update MSW mocks in `test/mocks/handlers.ts`

### Phase 3: Cleanup
1. Remove `GET /api/v1/agents/workflows/active` endpoint (when safe)
2. Remove backward compatibility code from frontend

---

## Acceptance Criteria

- [ ] New `GET /api/v1/workflows` endpoint returns paginated results
- [ ] All query parameters work as documented
- [ ] Response includes `pagination.total` for UI display
- [ ] Response includes `pagination.has_more` for infinite scroll support
- [ ] Sorting works on `created_at`, `updated_at`, `status`, `progress_percentage`
- [ ] Filtering works on `status` and `type`
- [ ] Search parameter filters by workflow name and type
- [ ] Performance: <100ms response time for limit=20 queries

---

## Related Files

- Frontend: `frontend/client/src/hooks/useWorkflows.ts` (lines 125-136)
- Backend: `services/layer4-agents/src/api/routes/workflows.py` (lines 490-503)
- Tests: `frontend/client/src/hooks/useWorkflows.test.ts`

---

## Notes

- **NO CLIENT-SIDE PAGINATION** will be implemented as a workaround
- The frontend will continue using the active endpoint as a proxy until backend support is available
- This is documented as a known limitation in code comments
