# Spec: Context Engine — Targets Admin Portal (`/context/targets`)

**Status:** Draft  
**Scope:** Full-stack — Layer 1 backend API additions + frontend page + hooks  
**Route:** `/context/targets`  
**Access tier:** `admin`

---

## 1. Problem Statement

Layer 1 (`services/layer1-ingestion`) has a fully-modelled `ScrapingTarget` entity with CRUD, validate, execute, and stats API endpoints at `/api/v1/ingestion/targets`. There is no dedicated UI for managing these targets. The existing `/context/sources` page (`SourceConfiguration.tsx`) wraps the same API but conflates two distinct concepts:

- **Source** — a captured document/page/file (evidence/provenance object)
- **Target** — an operational configuration defining *what* Layer 1 should crawl, monitor, or research

The Targets Admin Portal gives operators a dedicated control plane for defining, monitoring, and managing scraping targets — the upstream configuration that drives all of Layer 1's intelligence intake.

---

## 2. Object Model Clarification

```
Target   (what to crawl / research — this portal)
  ↓ produces
Source records   (what was captured — /context/sources)
  ↓ processed by
Ingestion Jobs   (execution runs — /context/ingestion/jobs)
  ↓ generates
SourceCorpus / AccountIntelligencePacket
  ↓ emits
Downstream pipeline events (L2, L3, L4)
```

---

## 3. Target Types Supported

The portal must support all target types defined in the `ScrapingTarget` model:

| Target Type (backend) | Product Label | Use Case |
|---|---|---|
| `SINGLE_PAGE` | Licensing Company | Single-page company profile intake |
| `PAGINATED` | Prospect Account | Paginated prospect research |
| `SPIDER` | Competitor / Industry Source | Deep-crawl competitor or industry site |
| `API_ENDPOINT` | CRM Account / Benchmark Source | API-based data intake |

Source categories (`source_category` field): `API`, `CRM`, `ERP`, `HRIS`, `MARKETING`, `FINANCE`, `PRODUCT`, `SUPPORT`, `GENERAL`.

---

## 4. Page Tabs

The `/context/targets` page uses horizontal tabs (consistent with the Value Fabric UX pattern):

| Tab | Content |
|---|---|
| **All Targets** | Full list with filters — default tab |
| **Scheduled** | Targets with `schedule.enabled = true`, sorted by next run |
| **Compliance Failures** | Targets with `status = ERROR` or recent compliance events |
| **Events** | Recent execution events across all targets (read-only log) |

---

## 5. Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PageHeader: "Targets"   [+ New Target]  [Refresh]                           │
│ Tabs: All Targets | Scheduled | Compliance Failures | Events                │
├──────────────────────────────────────────┬──────────────────────────────────┤
│  Filter bar: Search | Type | Status | Tag│  Right Rail (slide-in)           │
│                                          │  ┌────────────────────────────┐  │
│  Target list (table)                     │  │ Target Detail / Edit Form  │  │
│  ─ Name, URL, Type, Status badge         │  │ ─ Identity                 │  │
│  ─ Last run, Success/Error counts        │  │ ─ Crawl config             │  │
│  ─ Health score indicator                │  │ ─ Schedule                 │  │
│  ─ Tags                                  │  │ ─ Rate limits              │  │
│  ─ Row actions: Run | Pause | Archive    │  │ ─ Compliance               │  │
│                                          │  │ ─ Authentication           │  │
│  Stats strip (top of list):              │  │ ─ Job history              │  │
│  Total | Active | Paused | Error         │  │ ─ Live run status          │  │
│                                          │  └────────────────────────────┘  │
└──────────────────────────────────────────┴──────────────────────────────────┘
```

The right rail opens when a target row is clicked. It shows detail/edit mode. A "New Target" button opens the same right rail in create mode.

---

## 6. Functional Requirements

### 6.1 Target List (All Targets tab)

- Display all `ScrapingTarget` records for the authenticated tenant.
- Columns: Name, URL (truncated with tooltip), Type badge, Status badge, Last Run, Success / Error counts, Health score bar, Tags.
- Filter controls: free-text search (name/URL), Type dropdown, Status dropdown, Tag multi-select.
- Sort: by Name, Created At, Last Run, Status (default: Created At desc).
- Pagination: server-side, 25 per page.
- Row actions (inline): **Run** (trigger execute), **Pause/Resume** (toggle ACTIVE ↔ PAUSED), **Archive** (set ARCHIVED, requires confirmation).
- Bulk actions toolbar (appears when rows selected): Run Selected, Pause Selected, Archive Selected.
- Empty state: explains what a target is and offers "Create your first target" CTA.

### 6.2 Stats Strip

Rendered above the table using `GET /api/v1/ingestion/targets/stats`:
- Total targets, Active count, Paused count, Error count, Average health score.

### 6.3 Right Rail — Target Detail

Opens on row click. Shows read-only summary with an **Edit** button that switches to edit mode in-place.

Sections:
1. **Identity** — Name, Description, URL, URL Pattern, Target Type, Source Category, Tags, Status badge, Created by / at.
2. **Crawl Configuration** — Crawl path (FAST / BROWSER / FAST_WITH_FALLBACK), Extraction config (method, schema preview), Browser config (engine, headless, viewport).
3. **Schedule** — Enabled toggle, cron expression, timezone, max concurrent jobs.
4. **Rate Limits** — Requests/sec, requests/min, retry attempts, backoff strategy.
5. **Compliance** — Respect robots.txt toggle, crawl delay, PII redaction toggle, domain allow/block lists.
6. **Authentication** — Auth type badge, credentials reference (masked).
7. **Job History** — Last 10 jobs for this target: status, triggered by, started at, duration, pages crawled. Links to `/context/ingestion/jobs?targetId=<id>`.
8. **Live Run Status** — If a job is currently running against this target, show real-time progress (stage, current URL, pages crawled) via polling or SSE.

### 6.4 Right Rail — Create / Edit Form

Triggered by "+ New Target" or "Edit" button. Uses React Hook Form with Zod validation.

Fields:
- **Name** (required, string)
- **URL** (required, valid URL)
- **URL Pattern** (optional, regex)
- **Target Type** (required, select: SINGLE_PAGE / PAGINATED / SPIDER / API_ENDPOINT)
- **Source Category** (optional, select)
- **Description** (optional, textarea)
- **Tags** (optional, tag input)
- **Crawl Path** (select: FAST / BROWSER / FAST_WITH_FALLBACK)
- **Schedule** — enabled toggle; if enabled: cron expression input, timezone select
- **Rate Limit** — requests/sec, requests/min, retry attempts (numeric inputs)
- **Compliance** — respect robots.txt (toggle), PII redaction (toggle), crawl delay (numeric)
- **Authentication** — type select; if not NONE: credentials reference input

On submit: POST (create) or PUT (update) to Layer 1 API. Show inline field errors and server rejection messages. Disable submit during pending state.

### 6.5 Scheduled Tab

Filtered view of targets with `schedule.enabled = true`. Additional column: **Next Run** (derived from cron expression). Sorted by next run ascending.

### 6.6 Compliance Failures Tab

Filtered view: targets with `status = ERROR` or `error_count > 0`. Additional column: **Last Error At**. Sorted by last error descending.

### 6.7 Events Tab

Read-only log of recent execution events across all targets. Uses `GET /api/v1/ingestion/jobs` filtered to recent jobs, showing: target name, job status, triggered by, started at, pages crawled, duration. Paginated, 50 per page.

---

## 7. Backend Requirements

### 7.1 Existing Endpoints (already implemented — use as-is)

| Method | Path | Use |
|---|---|---|
| `GET` | `/api/v1/ingestion/targets` | List targets (paginated, filtered) |
| `POST` | `/api/v1/ingestion/targets` | Create target |
| `GET` | `/api/v1/ingestion/targets/stats` | Stats strip |
| `GET` | `/api/v1/ingestion/targets/{id}` | Target detail |
| `PUT` | `/api/v1/ingestion/targets/{id}` | Update target |
| `DELETE` | `/api/v1/ingestion/targets/{id}` | Delete target |
| `POST` | `/api/v1/ingestion/targets/{id}/validate` | Test/validate target |
| `POST` | `/api/v1/ingestion/targets/{id}/execute` | Trigger crawl job |
| `GET` | `/api/v1/ingestion/targets/{id}/decisions` | Crawl decisions log |

### 7.2 Missing Endpoints (must be added)

#### `PATCH /api/v1/ingestion/targets/{target_id}/status`

Lightweight status transition endpoint (ACTIVE ↔ PAUSED ↔ ARCHIVED). Avoids requiring a full PUT payload for simple pause/resume/archive actions.

**Request body:**
```json
{ "status": "PAUSED" }
```

**Response:** `ScrapingTargetDetail` (updated record)

**Validation:** Only allow transitions: ACTIVE→PAUSED, PAUSED→ACTIVE, ACTIVE→ARCHIVED, PAUSED→ARCHIVED. ARCHIVED is terminal (no transitions out).

**Tenant isolation:** Extract `tenant_id` from authenticated context. Confirm target belongs to tenant before update.

#### `POST /api/v1/ingestion/targets/batch`

Bulk operations on multiple targets. Reuses the existing `BatchOperationRequest` schema already defined in the L1 OpenAPI spec.

**Request body:**
```json
{
  "operation": "execute" | "pause" | "archive",
  "target_ids": ["uuid", ...]
}
```

**Response:** `{ "succeeded": [...], "failed": [...] }`

**Tenant isolation:** Filter `target_ids` to only those belonging to the authenticated tenant. Silently skip IDs that don't belong to the tenant (do not error).

### 7.3 OpenAPI Contract Updates

Both new endpoints must be added to the OpenAPI spec (`contracts/` and the generated `apps/web/src/api/generated/l1/index.ts`). The `TargetStatus` enum and `ScrapingTargetDetail` schema are already defined and must not change shape.

---

## 8. Frontend Architecture

### 8.1 New Files

| File | Purpose |
|---|---|
| `apps/web/src/pages/TargetsAdmin.tsx` | Page component — tabs, layout, orchestration |
| `apps/web/src/pages/TargetsAdmin.test.tsx` | Behavior tests |
| `apps/web/src/hooks/useTargets.ts` | TanStack Query hooks for all target operations |
| `apps/web/src/hooks/useTargets.test.ts` | Hook unit tests |

### 8.2 Hook Surface (`useTargets.ts`)

```typescript
useTargets(filters: TargetFilters)           // list with pagination
useTarget(id: string)                        // single target detail
useTargetStats()                             // stats strip
useCreateTarget()                            // mutation
useUpdateTarget()                            // mutation (full PUT)
useUpdateTargetStatus()                      // mutation (PATCH status)
useDeleteTarget()                            // mutation
useExecuteTarget()                           // mutation (trigger run)
useValidateTarget()                          // mutation (test connection)
useBatchTargetOperation()                    // mutation (bulk)
useTargetJobs(targetId: string)              // recent jobs for a target
```

All hooks use `apiGet` / `apiPost` / `apiPut` / `apiPatch` / `apiDelete` from `@/api/typedClient`. Response types use `l1.components['schemas']['ScrapingTargetDetail']` and `l1.components['schemas']['ScrapingTargetSummary']` as generics. Query keys registered in `queryKeys.ts` under a `targets` namespace.

### 8.3 Router Registration

Add to `apps/web/src/shell/router.tsx`:
```
{ path: "/context/targets", element: <ProtectedRoute requiredTier="admin"><TargetsAdmin /></ProtectedRoute> }
```

### 8.4 Navigation

Add a "Targets" child entry under the Context Engine section in `apps/web/src/components/layout/Layout.tsx` `NAV_DOMAINS` (or the relevant nav structure), visible at `admin` tier. Label: **Targets**. Icon: `Target` (already imported in Layout.tsx).

### 8.5 Breadcrumb

Add `targets: "Targets"` to the `domainLabels` map in `Layout.tsx`'s `getBreadcrumbs` function so the breadcrumb reads: `Context Engine > Targets`.

---

## 9. Design System Compliance

- Use `PageHeader` from `@/components/ui/fabric/PageHeader`.
- Use `FabricCard` / `SectionCard` for right-rail sections.
- Use `DataTable` from `@/components/ui/fabric/DataTable` for the target list.
- Use `FilterBar` from `@/components/ui/fabric/FilterBar` for filter controls.
- Status badges: use `Badge` variants — `success` (ACTIVE), `warning` (PAUSED), `destructive` (ERROR), `secondary` (ARCHIVED).
- Right rail: use `Sheet` (shadcn) with `side="right"`, consistent with existing detail panels.
- Forms: React Hook Form + Zod schema validation. Field-level errors. Submission pending state disables the submit button.
- Loading states: `Skeleton` rows in the table while fetching.
- Empty state: use `empty.tsx` primitive with contextual copy.
- Error state: use `ErrorBoundary` + `QueryState` error display.
- Dark mode: all surfaces must use semantic tokens only — no hard-coded colors.

---

## 10. Tenant Isolation Requirements

- All API calls include the authenticated tenant context (handled by `apiGet`/`apiPost` wrappers via the auth header).
- Backend `PATCH /status` and `POST /batch` endpoints must verify target ownership against `tenant_id` from the JWT context — not from the request body.
- Frontend must never display or allow mutation of targets from other tenants. The API enforces this; the frontend must not attempt cross-tenant operations.
- Query cache keys must be namespaced by tenant: `['targets', tenantId, ...]`.

---

## 11. Acceptance Criteria

### Navigation
- [ ] `/context/targets` is accessible to `admin`-tier users.
- [ ] A "Targets" nav entry appears in the Context Engine section of the sidebar for admin users.
- [ ] Breadcrumb reads "Context Engine > Targets".
- [ ] Non-admin users receive a 403 / redirect from `ProtectedRoute`.

### List View
- [ ] All targets for the tenant are listed with correct columns.
- [ ] Stats strip shows accurate totals from the stats endpoint.
- [ ] Filtering by status, type, and search text narrows the list correctly.
- [ ] Pagination works (next/prev, page size 25).
- [ ] Clicking a row opens the right rail with target detail.

### Create / Edit
- [ ] "+ New Target" opens the right rail in create mode with an empty form.
- [ ] Required field validation prevents submission with missing Name or URL.
- [ ] Invalid URL format shows a field-level error.
- [ ] Successful create adds the target to the list and shows a toast.
- [ ] Successful edit updates the row in-place and shows a toast.
- [ ] Server rejection (4xx) shows the error message in the form without losing user input.

### Status Actions
- [ ] "Pause" on an ACTIVE target transitions it to PAUSED via `PATCH /status`.
- [ ] "Resume" on a PAUSED target transitions it to ACTIVE.
- [ ] "Archive" shows a confirmation dialog before calling `PATCH /status` with ARCHIVED.
- [ ] Archived targets cannot be resumed (action is absent/disabled).

### Bulk Actions
- [ ] Selecting multiple rows reveals the bulk action toolbar.
- [ ] "Run Selected" triggers `POST /batch` with `operation: execute`.
- [ ] "Pause Selected" triggers `POST /batch` with `operation: pause`.
- [ ] Partial failures (some targets failed) show a warning toast with the count.

### Right Rail — Detail
- [ ] All target fields are displayed correctly.
- [ ] Job history shows the last 10 jobs with correct status and timestamps.
- [ ] If a job is currently running, a live status section shows stage and current URL (polling every 5s).

### Tabs
- [ ] Scheduled tab shows only targets with `schedule.enabled = true`, sorted by next run.
- [ ] Compliance Failures tab shows only targets with `status = ERROR` or `error_count > 0`.
- [ ] Events tab shows recent jobs across all targets, paginated.

### Backend
- [ ] `PATCH /api/v1/ingestion/targets/{id}/status` rejects invalid transitions with 422.
- [ ] `PATCH /api/v1/ingestion/targets/{id}/status` returns 404 if target does not belong to tenant.
- [ ] `POST /api/v1/ingestion/targets/batch` silently skips IDs not belonging to the tenant.
- [ ] Both new endpoints are reflected in the OpenAPI contract and generated TypeScript types.

### Quality
- [ ] TypeScript compiles without errors (`pnpm --dir apps/web tsc --noEmit`).
- [ ] No raw `apiClient` calls in hooks (enforced by `check:no-raw-api-client-in-hooks`).
- [ ] No `@/api/legacy` imports.
- [ ] Behavior tests cover: list render, create flow, status transition, bulk action, empty state, error state.
- [ ] Backend tests cover: status transition validation, tenant isolation for PATCH and batch endpoints.

---

## 12. Implementation Order

1. **Backend — `PATCH /status` endpoint** in `services/layer1-ingestion/src/api/routes/` with tenant isolation and transition validation. Unit tests.
2. **Backend — `POST /batch` endpoint** (reuse existing `BatchOperationRequest` schema). Unit tests.
3. **OpenAPI contract update** — add both endpoints to the spec in `contracts/`. Regenerate `apps/web/src/api/generated/l1/index.ts`.
4. **`useTargets.ts` hook** — full hook surface using typed client. Query key registration. Unit tests.
5. **`TargetsAdmin.tsx` page** — tabs, stats strip, filter bar, target table, row actions, bulk toolbar, empty/loading/error states.
6. **Right rail — detail panel** — read-only sections, job history, live run status polling.
7. **Right rail — create/edit form** — React Hook Form + Zod, all fields, submission states.
8. **Router + navigation wiring** — add route, nav entry, breadcrumb label.
9. **Behavior tests** (`TargetsAdmin.test.tsx`, `useTargets.test.ts`).
10. **Validation** — `pnpm --dir apps/web tsc --noEmit`, lint, test run.

---

## 13. Out of Scope

- Proxy pool management (separate concern, existing `/context/sources` area).
- Compliance log viewer beyond the Compliance Failures tab filter (full compliance log is a governance concern).
- Target versioning / history (not in the current `ScrapingTarget` model).
- Non-admin users viewing targets in read-only mode (deferred; admin-only for now).
- Replacing or modifying `/context/sources` (it remains a peer page for captured source records).
