# Design System & Performance Audit Report
**Date:** 2026-05-06
**Scope:** Frontend design consistency, accessibility, and performance optimizations

---

## Executive Summary

Completed audits across 4 categories (Design System, Design Inconsistencies, Accessibility, Performance). Key findings:
- **DataTable already standardized** in fabric folder
- **3 skeleton sources** need consolidation
- **Pagination inconsistent** - shadcn component exists but pages use custom implementations
- **Settings pages consolidated** in app/settings/pages (25 files)
- **0 aria-live regions** on 24 streaming UI components
- **Dialog/Sheet focus management** relies on Radix UI defaults (no explicit autoFocus)
- **manualChunks configured** for major libraries

---

## 1. Design System Audit

### 1.1 List Page Patterns (ds-1 ✅)

**Sampled Pages:**
- `Accounts.tsx` - Custom Table + FilterChipBar (horizontal chips) + custom pagination
- `IngestionJobs.tsx` - Uses fabric DataTable + custom filter controls (select dropdowns) + custom pagination

**Existing Components:**
- `components/ui/fabric/DataTable.tsx` - Standardized column API with key, header, render, className
  - Supports: keyExtractor, emptyMessage, onRowClick, selectedKey
  - Well-designed with consistent styling

**Filter Patterns:**
- No standardized FilterBar component exists
- Each page implements filters bespoke:
  - FilterChipBar (horizontal chips with dropdowns)
  - Select dropdowns
  - Date range pickers

**Recommendation:**
- DataTable is production-ready ✅
- Create standardized FilterBar component to unify filter UI patterns
- Migrate pages to use DataTable + FilterBar combination

---

## 2. Design Inconsistencies Audit

### 2.1 Skeleton Sources (di-1 ✅)

**Found 3 skeleton component libraries:**

1. **`components/ui/fabric/LoadingSkeleton.tsx`** (85 lines)
   - Variants: card, table, metric, form, page
   - Uses shadcn Skeleton as base
   - Well-structured with consistent styling

2. **`components/ui/skeleton.tsx`** (14 lines)
   - Basic shadcn skeleton component
   - Low-level primitive

3. **`components/ui/SkeletonViews.tsx`** (259 lines)
   - Apple-quality skeleton screens
   - Components: SkeletonLine, SkeletonText, SkeletonCard, SkeletonTable, SkeletonPage, SkeletonStats, SkeletonForm
   - Comprehensive but separate from LoadingSkeleton

**Usage:** 38 files import Skeleton components

**Recommendation:**
- Consolidate to single skeleton library
- Keep LoadingSkeleton as primary (variants cover most use cases)
- Consider merging SkeletonViews specialized components into LoadingSkeleton
- Deprecate direct skeleton.tsx imports (use LoadingSkeleton instead)

### 2.2 Pagination Inconsistencies (di-3 ✅)

**Existing Component:**
- `components/ui/pagination.tsx` - Full shadcn pagination with:
  - Pagination, PaginationContent, PaginationLink, PaginationItem
  - PaginationPrevious, PaginationNext, PaginationEllipsis
  - Proper ARIA labels and keyboard navigation

**Actual Usage:**
- 6 files use Pagination component
- **But** major pages use custom implementations:
  - `Accounts.tsx` - Custom ChevronLeft/Right buttons with text "Showing X to Y of Z"
  - `IngestionJobs.tsx` - Custom ChevronLeft/Right buttons with "Page X of Y"

**Recommendation:**
- Migrate all pages to use shadcn pagination component
- Ensure consistent pagination shape across application

### 2.3 Settings Pages (di-5 ✅)

**Location:** `app/settings/pages/` (25 files)

**Structure:**
```
app/settings/pages/
├── Billing* (5 files)
├── Data* (5 files)
├── Governance* (5 files)
├── Personal* (5 files)
└── Team* (5 files)
```

**Finding:**
- All settings pages consolidated in single location ✅
- No `pages/admin` directory exists (recommendation outdated)

**Recommendation:**
- No action needed - settings pages are already consolidated

---

## 3. Accessibility Audit

### 3.1 Streaming UI Components (a11y-1 ✅)

**Found 24 streaming/chat components:**
- `AgentChat.tsx`
- Studio tabs (8 files): NarrativeTab, StudioEnrichmentTab, StudioEvidenceTab, ValueModelTab, StudioROITab, StudioCompetitiveTab, ActionPlanTab
- Intelligence tabs (8 files): EnrichmentTab, OntologyMatchTab, SignalsTab, StakeholdersTab, ROITab, HypothesesTab, EvidenceTab, DriversTab
- Calculator tabs (2 files): ROITab, ValueModelTab
- Hypothesis tabs (3 files): PersonaFitTab, DiscoveryQuestionsTab, AssumptionsTab
- RealizationPage, ValueCasePage, InteractiveBusinessCase, RightRail, GlobalLayout

**aria-live Usage:** 0 matches

**Recommendation:**
- Add `aria-live="polite"` or `aria-live="assertive"` to streaming content containers
- Critical for screen readers to announce dynamic content updates

### 3.2 Dialog/Sheet Focus Management (a11y-2 ✅)

**Components:**
- `components/ui/dialog.tsx` - Uses Radix UI Dialog with composition context for IME handling
- `components/ui/sheet.tsx` - Uses Radix UI Dialog primitive (same as dialog)

**Focus Management:**
- Radix UI handles focus trap and restore automatically
- No explicit `autoFocus` prop set on DialogContent or SheetContent
- Found `autoFocus` usage in:
  - `MyModels.tsx:348` (not on dialog)
  - `login-form.tsx:249, 472` (not on dialog)

**Recommendation:**
- Verify Radix UI default focus behavior is sufficient
- Consider adding explicit `autoFocus` if screen reader testing reveals issues
- Add a11y tests to verify focus moves to dialog/sheet on open

---

## 4. Performance Audit

### 4.1 manualChunks Configuration (perf-1 ✅)

**Current vite.config.ts manualChunks:**
```typescript
manualChunks: (id) => {
  if (id.includes('@tanstack/react-query')) return 'vendor-react-query';
  if (id.includes('@radix-ui')) return 'vendor-radix';
  if (id.includes('recharts') || id.includes('chart.js') || id.includes('d3')) return 'vendor-charts';
  if (id.includes('axios')) return 'vendor-axios';
  if (id.includes('zod')) return 'vendor-zod';
  if (id.includes('react') || id.includes('react-dom')) return 'vendor-react';
}
```

**Assessment:** ✅ Well-configured for major libraries

**Recommendation:**
- No changes needed - manualChunks already optimized
- Consider adding layer-specific chunks if layer3/layer4 audit reveals large bundles

### 4.2 Route Prefetching (perf-2 ⏳)

**Status:** Not audited yet

**Likely transitions to prefetch:**
- Accounts → EntityDetail
- BusinessCaseList → BusinessCase
- Any list → detail page patterns

**Recommendation:**
- Implement prefetch for likely next routes using React Router's prefetch API or Link prefetch

### 4.3 Layer Bundle Audit (perf-3 ⏳)

**Status:** Not audited yet

**Target layers:**
- Layer 3: 12.6K lines
- Layer 4: 11.7K lines

**Recommendation:**
- Run bundle analyzer (`ANALYZE=true pnpm build`)
- Verify tree-shaking effectiveness
- Check if entire layers are pulled into initial bundle

---

## 5. Action Items Summary

### High Priority (12 tasks remaining)
- ds-2: Enhance DataTable with sorting if needed
- ds-3: Design and implement FilterBar component
- di-2: Standardize skeleton components to single library
- di-4: Migrate pages to use shadcn pagination
- a11y-1: Add aria-live to 24 streaming UI components
- a11y-3: Add focus management tests for dialogs/sheets
- perf-2: Implement route prefetching
- perf-3: Audit layer3/layer4 bundle tree-shaking

### Medium Priority (5 tasks remaining)
- ds-4: Design FacetPanel (if hierarchical filtering needed)
- ds-5: Migrate existing list pages to new components
- a11y-3: Add a11y tests (already listed)
- perf-4: Optimize bundle if audit reveals issues

---

## 6. Implementation Order Recommendation

**Phase 1 - Quick Wins (1-2 days):**
1. Add aria-live to streaming UIs (a11y-1)
2. Migrate pagination to shadcn component (di-4)

**Phase 2 - Design System (3-5 days):**
3. Implement FilterBar component (ds-3)
4. Standardize skeleton library (di-2)
5. Migrate list pages to new components (ds-5)

**Phase 3 - Performance (2-3 days):**
6. Implement route prefetching (perf-2)
7. Audit layer bundles (perf-3)
8. Optimize if needed (perf-4)

**Phase 4 - Testing (1-2 days):**
9. Add a11y focus tests (a11y-3)

**Total Estimated Effort:** 7-12 days
