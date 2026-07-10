# GDPR Admin UI Specification — Fabric 4L

## Overview

React-based administrative interface for managing GDPR/CCPA data deletion requests. Provides secure, audit-friendly workflows for initiating tenant erasure, tracking progress, and exporting immutable reports.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GDPR Admin Module                     │
├─────────────────┬──────────────────┬────────────────────┤
│  Request Form   │  Status Tracker  │   Report Viewer     │
│   (Modal/Page)  │  (Polling UI)    │ (PDF/CSV Export)    │
└─────────────────┴──────────────────┴────────────────────┘
           │                │                   │
           └────────────────┴───────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   Fabric 4L API            │
              │   /admin/gdpr/*            │
              └────────────────────────────┘
```

## Component: GDPRDeletionRequestForm

### Purpose
Admin-only form to initiate a tenant data deletion (right-to-erasure).

### Props
```typescript
interface GDPRDeletionRequestFormProps {
  /** Available tenants for deletion (admin scoped) */
  tenants: TenantOption[];
  /** Callback after successful submission */
  onSubmitted: (requestId: string) => void;
  /** API client instance */
  apiClient: FabricAPIClient;
}

interface TenantOption {
  id: string;
  name: string;
  recordCount: number;
  lastActivity: string;
  region: string; // eu/us for GDPR vs CCPA labelling
}
```

### UI Flow

1. **Tenant Selection**
   - Searchable dropdown with tenant metadata
   - Displays record count and data region (EU flag for GDPR, US flag for CCPA)
   - Warns if tenant > 1M records (safety threshold approaching)

2. **Reason Input**
   - Required dropdown: `["GDPR Article 17", "CCPA Section 1798.105", "Business Termination", "Data Breach Remediation", "Other"]`
   - Free-text notes field (max 500 chars)

3. **Confirmation Step**
   - Type-exact confirmation: user must type `delete {tenant_id}` into a text field
   - Checkbox: `"I understand this action is irreversible and will be logged for regulatory inspection"`
   - Submit button disabled until both confirmation and checkbox are satisfied

4. **2FA Admin Re-Authentication**
   - Before submission, admin must re-enter their MFA TOTP code
   - API validates MFA via `/auth/verify-mfa` endpoint

### State Machine
```
[Idle] ──select tenant──> [TenantSelected]
[TenantSelected] ──enter reason──> [ReasonEntered]
[ReasonEntered] ──type confirmation──> [Confirmed]
[Confirmed] ──check acknowledge box──> [Acknowledged]
[Acknowledged] ──enter MFA──> [MFAValid]
[MFAValid] ──submit──> [Submitting] ──202──> [Submitted]
                                 ──409──> [AlreadyInProgress]
                                 ──422──> [SafetyLimitExceeded]
                                 ──4xx──> [Error]
```

### Validation Rules
- `tenant_id`: required, must exist in admin's scoped tenant list
- `confirmation`: must exactly match `delete {tenant_id}` (case-insensitive)
- `reason`: required, min 5 characters
- MFA code: 6 digits, verified server-side

### Accessibility
- All form fields have associated `<label>` elements
- Error messages announced via `aria-live="polite"`
- Confirmation text field uses `aria-describedby` linking to warning text
- Color alone is never used to convey status (icons + text)

---

## Component: DeletionStatusTracker

### Purpose
Real-time polling UI showing deletion job progress.

### Props
```typescript
interface DeletionStatusTrackerProps {
  requestId: string;
  /** Polling interval in ms (default: 3000) */
  pollInterval?: number;
  /** Callback when job reaches terminal state */
  onComplete?: (status: DeletionStatus) => void;
  apiClient: FabricAPIClient;
}
```

### Visual Design

```
┌─────────────────────────────────────────┐
│ Deletion Job #req-550e8400-e29b-41d4   │
│ Tenant: acme-corp (us-east)             │
│                                         │
│ Progress: [████████████░░░░░░] 67%      │
│                                         │
│ L1 Documents    ✅  1,245 rows  1.2s   │
│ L2 Entities     ✅    892 rows  0.8s   │
│ L3 Knowledge    ✅  3,401 rows  2.4s   │
│ L4 Workflows    ✅    156 rows  0.3s   │
│ L5 Ground Truth 🔄    In progress...    │
│ L6 Benchmarks   ⏳    Waiting...        │
│                                         │
│ Verification: Pending                   │
│ Audit Hash:  (computed on completion)   │
│                                         │
│ [Cancel]*  [View Report] (disabled)     │
└─────────────────────────────────────────┘
```

*Cancel requires separate admin approval and logs a cancellation audit event

### Behavior
- Polls `GET /admin/gdpr/deletion-status/{request_id}` every 3 seconds
- Uses exponential backoff when job is in terminal state
- Displays per-layer progress with color-coded status indicators
- Shows animated spinner during active layers, checkmark for completed
- Verification badge: green shield when passed, red warning when failed
- Auto-scrolls to keep active layer in view

### Polling Lifecycle
```
start polling (3s interval)
    │
    ▼
┌──────────┐
│ IN_PROGRESS│◄─────────────────────┐
└──────────┘                       │
    │                              │
    ▼                              │
terminal? ──yes──> stop polling ──┘
    │
    no
    │
    └── wait 3s ──> poll again
```

### Accessibility
- Progress bar uses `role="progressbar"` with `aria-valuenow`
- Status changes announced via `aria-live="assertive"`
- Color-blind friendly: icons (✅ 🔄 ⏳ ❌) accompany all colors

---

## Component: DeletionReportViewer

### Purpose
Display the complete, immutable deletion report for regulatory inspection.

### Props
```typescript
interface DeletionReportViewerProps {
  requestId: string;
  /** Whether to show full audit hash chain */
  showAuditChain?: boolean;
  apiClient: FabricAPIClient;
}
```

### Sections

#### 1. Summary Header
- Request ID (click to copy)
- Tenant ID and region
- Initiated by (admin name + user ID)
- Initiated at (local timezone + UTC)
- Overall status badge (Completed / Partial / Failed)
- Total records deleted (human-formatted)
- Verification status with icon

#### 2. Audit Integrity Panel
```
┌────────────────────────────────────────────────────┐
│ 🔒 Audit Integrity                                 │
│                                                    │
│ Report Hash:    a3f7b2...e9d1 (SHA-256)           │
│ Chain Hash:     8c4e12...7f3a                      │
│ Previous:       2d9a55...4b8c (block 12)           │
│ Immutable:      ✅ Database append-only enforced   │
│                                                    │
│ [Verify Chain]  [Download Signed Certificate]      │
└────────────────────────────────────────────────────┘
```

#### 3. Per-Layer Detail (expandable accordion)
Each layer shows:
- Layer name and description
- Status badge
- Tables affected with row counts
- Duration in milliseconds
- Error message (if failed/partial, highlighted in red)
- SQL preview (admin debug mode only, behind feature flag)

#### 4. Timeline
```
09:14:23.412  Request received
09:14:23.415  Safety check passed (45,678 total records)
09:14:23.891  L1 deletion started
09:14:24.234  L1 completed — 12,345 rows in 343ms
...
09:14:31.002  Verification pass — 0 remaining rows
09:14:31.003  Audit log written — hash: a3f7b2...
```

### Export Functionality

#### PDF Export
- Library: `react-pdf` or server-side via `puppeteer`
- Content: Full report with audit hashes, layer details, timeline
- Header: "Fabric 4L — GDPR Deletion Report — Confidential"
- Footer: Page numbers, generation timestamp, digital signature placeholder
- Filename: `fabric4l-gdpr-deletion-{tenant_id}-{request_id}-{date}.pdf`

#### CSV Export
- Flattened format for spreadsheet analysis
- One row per (layer, table) combination
- Columns: `request_id, tenant_id, layer, table, records_deleted, duration_ms, status, error, timestamp`
- Filename: `fabric4l-gdpr-deletion-{request_id}.csv`

### Print Styles
- `@media print` hides navigation, buttons, and polling UI
- Audit hash is prominently displayed in header
- Page breaks between major sections

---

## Route Configuration

```typescript
// routes/gdpr.tsx
export const gdprRoutes = [
  {
    path: '/admin/gdpr',
    element: <GDPRDashboard />,
    children: [
      { index: true, element: <GDPRDeletionRequestForm /> },
      { path: 'status/:requestId', element: <DeletionStatusTracker /> },
      { path: 'report/:requestId', element: <DeletionReportViewer /> },
    ],
  },
];
```

---

## State Management

Uses React Query for server state:

```typescript
// hooks/useDeletionJob.ts
export function useDeletionJob(requestId: string) {
  return useQuery({
    queryKey: ['gdpr', 'deletion', requestId],
    queryFn: () => apiClient.getDeletionStatus(requestId),
    refetchInterval: (data) =>
      data?.status === 'in_progress' ? 3000 : false,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useDeleteTenant() {
  return useMutation({
    mutationFn: (payload: DeleteTenantPayload) =>
      apiClient.initiateDeletion(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['gdpr', 'jobs'] });
      navigate(`/admin/gdpr/status/${data.request_id}`);
    },
  });
}
```

---

## Security Considerations

1. **Route Guard**: All `/admin/gdpr/*` routes wrapped in `<RequireAdmin>` component
2. **MFA Re-auth**: Deletion submission requires fresh TOTP verification
3. **CSRF Protection**: All mutations include `X-CSRF-Token` header
4. **Audit Client Actions**: UI-level events (view report, export PDF) logged via
   `POST /audit/client-event` beacon
5. **No Client-Side Secrets**: Audit hashes displayed but never generated client-side
6. **Session Timeout**: Auto-redirect to login after 15 minutes of inactivity on GDPR pages

---

## Accessibility Checklist

- [ ] Keyboard navigable (Tab order, Enter/Space activation)
- [ ] Screen reader tested (NVDA, VoiceOver)
- [ ] Color contrast WCAG AA (4.5:1 normal text, 3:1 large text)
- [ ] Focus indicators visible on all interactive elements
- [ ] Reduced motion support (`prefers-reduced-motion`)
- [ ] Semantic HTML (`<main>`, `<section>`, `<h1>`–`<h3>` hierarchy)
