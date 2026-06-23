# Global Search Feature

## Overview

The Global Search feature provides a unified search experience across the Fabric4L platform, allowing users to search for accounts, signals, evidence, value cases, formulas, benchmarks, and other entities from a single interface.

## Architecture

### Phase 1 Implementation (Current)

The Phase 1 implementation focuses on frontend UX with a federated search contract:

```
Frontend (apps/web)
├── GlobalSearchDialog (cmdk-based command palette)
├── useGlobalSearch hook (TanStack Query + debouncing)
├── searchApiClient (typed API client)
└── Mock data + MSW handlers for testing

Backend (Future - Phase 2)
├── Search Orchestrator (federated across layers)
├── L3 Knowledge Graph search
├── L4 Agents search
├── L5 Ground Truth search
└── L6 Benchmarks search
```

### Components

#### Frontend Components

- **GlobalSearchDialog** (`apps/web/src/components/search/GlobalSearchDialog.tsx`)
  - cmdk-based command palette
  - Keyboard shortcut: Ctrl/Cmd + K
  - Real-time search with debouncing
  - Grouped results by entity type

- **useGlobalSearch** (`apps/web/src/hooks/useGlobalSearch.ts`)
  - TanStack Query integration
  - 300ms debounce
  - Result caching (5 minutes)
  - Tenant/account context support

- **searchApiClient** (`apps/web/src/api/search.ts`)
  - Typed API client for `/v1/search` endpoint
  - URL generation helpers
  - Tenant-scoped URL validation

- **SearchResultItem** (`apps/web/src/components/search/SearchResultItem.tsx`)
  - Individual result display
  - Icon mapping by entity type
  - Score display

- **SearchResultsList** (`apps/web/src/components/search/SearchResultsList.tsx`)
  - Grouped results by type
  - Type ordering (accounts, signals, evidence, etc.)

- **State Components**
  - SearchEmptyState
  - SearchLoadingState
  - SearchErrorState

#### Backend API Contract

**Endpoint:** `GET /v1/search`

**Query Parameters:**
- `q` (required): Search query string
- `scope` (optional): `tenant` or `account` (default: `tenant`)
- `account_id` (optional): Account ID for account-scoped search
- `types` (optional): Comma-separated entity type filters
- `limit` (optional): Results per type (default: 5)
- `cursor` (optional): Pagination cursor

**Response Schema:**
```typescript
{
  query: string;
  scope: "tenant" | "account";
  tenant_id: string;
  account_id?: string;
  results: {
    accounts?: SearchResult[];
    signals?: SearchResult[];
    evidence?: SearchResult[];
    // ... other entity types
  };
  total_by_type: Record<string, number>;
  processing_time_ms: number;
}
```

**SearchResult Schema:**
```typescript
{
  id: string;
  type: SearchResultType;
  title: string;
  subtitle?: string;
  excerpt?: string;
  url: string;
  tenant_id: string;
  account_id?: string;
  score?: number;
  source_layer?: "l3" | "l4" | "l5" | "l6" | "frontend_mock";
  metadata?: Record<string, unknown>;
}
```

### Canonical Routes

**Global search page:**
```
/t/:tenantSlug/search?q=...
```

**Account-scoped search:**
```
/t/:tenantSlug/accounts/:accountId/search?q=...
```

**Route-aware search (modal state):**
```
/t/acme/accounts/acc_123/intelligence/signals?search=open-risk&entity=signal_123
```

## Security

### Tenant Isolation (Non-Negotiable)

- **Never search across tenants** unless system-admin mode is explicitly implemented
- Backend must derive tenant from verified AuthContext (never trust tenantSlug from URL)
- All search queries must include tenant_id from RequestContext
- Results must be filtered by tenant_id before returning to frontend
- No raw cross-tenant graph/entity IDs in results

### Account Access Control

- Account-scoped search must verify user has access to the account
- Account membership check via existing account context store
- Results must be filtered by account_id when scope=account

### Result URL Security

- Result URLs must not expose inaccessible entities
- URL generation must respect user permissions
- No admin/system resources in normal user search

## Usage

### For Users

1. **Open Search:**
   - Press `Ctrl+K` (Windows/Linux) or `Cmd+K` (Mac)
   - Or click the search button in the header

2. **Search:**
   - Type your query in the search input
   - Results appear grouped by entity type
   - Click any result to navigate

3. **Keyboard Shortcuts:**
   - `Ctrl+K` / `Cmd+K`: Open search
   - `Escape`: Close search
   - `Arrow keys`: Navigate results
   - `Enter`: Select result

### For Developers

#### Using the search API client:

```typescript
import { search } from "@/api/search";

const response = await search({
  q: "reconciliation",
  scope: "tenant",
  types: ["evidence", "signals"],
  limit: 10,
});
```

#### Using the useGlobalSearch hook:

```typescript
import { useGlobalSearch } from "@/hooks/useGlobalSearch";

const { data, isLoading, search, clearSearch } = useGlobalSearch({
  tenantSlug: "acme",
  accountId: "acc_123",
});

// Trigger search
search("meridian");
```

#### Using the GlobalSearchDialog component:

```typescript
import { GlobalSearchDialog } from "@/components/search";

<GlobalSearchDialog
  open={isSearchOpen}
  onOpenChange={setIsSearchOpen}
  tenantSlug="acme"
  accountId={selectedAccountId}
/>
```

## Testing

### E2E Tests

Location: `apps/web/e2e/global-search.spec.ts`

Tests cover:
- Keyboard shortcut (Ctrl+K / Cmd+K)
- Click trigger from header
- Search and display results
- Result navigation
- Tenant-scoped URLs
- Empty state
- Loading state
- Dialog close behavior
- Result grouping by type

Run tests:
```bash
pnpm --dir apps/web run test:e2e global-search.spec.ts
```

### Mock Data

Location: `apps/web/src/test/mocks/searchMocks.ts`

Mock data includes:
- 2 accounts
- 2 signals
- 2 evidence items
- 1 stakeholder
- 1 value driver
- 1 value case
- 1 formula
- 1 benchmark
- 1 value pack
- 1 graph entity
- 1 agent thread
- 1 workflow run
- 1 deliverable

### MSW Handler

Location: `apps/web/src/test/mocks/handlers.ts`

The MSW handler intercepts `/api/v1/search` requests and returns mock data based on the query string.

## Entity Types

The following entity types are supported in Phase 1:

### P0 (Priority)
- **account**: CRM accounts
- **signal**: Intelligence signals
- **evidence**: Governance evidence
- **value_case**: Business value cases
- **formula**: ROI formulas
- **benchmark**: Industry benchmarks

### P1 (Future)
- **stakeholder**: Account stakeholders
- **value_driver**: Value drivers
- **value_pack**: Value packs
- **agent_thread**: AI agent conversations
- **workflow_run**: Workflow executions

### P2 (Future)
- **graph_entity**: Knowledge graph entities
- **deliverable**: Exported deliverables

## Future Enhancements (Phase 2)

### Backend Federated Search

1. **L3 Integration**
   - Connect to existing hybrid_search.py
   - Map graph entities to SearchResult format
   - Tenant-scoped queries

2. **L4 Integration**
   - Account search via accounts API
   - Agent thread search
   - Workflow run search

3. **L5 Integration**
   - Value case search
   - Evidence search
   - Ground truth validation search

4. **L6 Integration**
   - Benchmark search
   - Formula search
   - Value pack search

5. **Search Orchestrator**
   - Parallel queries to all layers
   - Result merging and ranking
   - Caching layer (Redis)
   - Performance optimization

### Frontend Enhancements

1. **Advanced Search UI**
   - Filter by type
   - Filter by date range
   - Filter by account
   - Save searches

2. **Search Analytics**
   - Track search queries
   - Track result clicks
   - Popular searches

3. **Recent Searches**
   - Local storage persistence
   - Quick access to recent queries

### Performance

1. Search debouncing optimization
2. Result caching strategy
3. Pagination for large result sets
4. Search suggestions/autocomplete

## Troubleshooting

### Search dialog not opening

- Check that AppShell is rendered
- Verify keyboard shortcut listener is attached
- Check browser console for errors

### No results appearing

- Verify MSW handler is registered
- Check mock data filter logic
- Ensure query string matches mock data

### URLs not tenant-scoped

- Check generateSearchResultUrl function
- Verify tenantSlug is passed correctly
- Check URL generation logic

## Related Documentation

- [API Reference](../API_REFERENCE.md)
- [Architecture](../architecture/)
- [Security](../SECURITY.md)
- [AGENTS.md](../../AGENTS.md)
