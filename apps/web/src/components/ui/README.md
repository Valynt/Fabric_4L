# UI Components Migration Guide

## Skeleton Hierarchy

### Canonical Hierarchy

```
components/ui/skeleton.tsx
  → Low-level shadcn primitive for basic shapes
  → Import: import { Skeleton } from "@/components/ui/skeleton"

components/ui/SkeletonViews.tsx
  → Apple-quality page-level skeleton system
  → Import: import { PageSkeleton, CardGridSkeleton, DetailPanelSkeleton } from "@/components/ui/SkeletonViews"
```

### Migration Rules

**For low-level shapes (buttons, inputs, text lines):**
```typescript
import { Skeleton } from "@/components/ui/skeleton";

<Skeleton className="h-4 w-24" />
```

**For page-level loading states:**
```typescript
import { PageSkeleton, CardGridSkeleton, DetailPanelSkeleton } from "@/components/ui/SkeletonViews";

<PageSkeleton />
<CardGridSkeleton count={3} />
<DetailPanelSkeleton />
```

**Do not use:**
```typescript
// DEPRECATED - competing export removed from WfPrimitives
import { Skeleton } from "@/components/WfPrimitives";
```

### Pages to Migrate

High-usage pages that should migrate to SkeletonViews:
- Accounts.tsx
- FormulaList.tsx
- IngestionJobs.tsx
- BusinessCaseList.tsx

### Example Migration

**Before:**
```typescript
import { Skeleton } from "@/components/WfPrimitives";

// Custom skeleton markup
<div className="space-y-4">
  <Skeleton className="h-8 w-48" />
  <Skeleton className="h-4 w-full" />
</div>
```

**After:**
```typescript
import { PageSkeleton } from "@/components/ui/SkeletonViews";

<PageSkeleton />
```

### Benefits

- Clear hierarchy: primitive vs page-level
- No competing Skeleton exports
- Consistent Apple-quality loading states
- Reduced boilerplate in pages
