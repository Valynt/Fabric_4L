/**
 * Value Studio (mission-led) — loading skeletons (contract §10, FE-LOAD-001).
 *
 * Geometry-matched to the composed page (header → journey → mission strip →
 * impact row → two-column grid) so loading never shifts layout when the
 * projection arrives. Decorative skeletons are aria-hidden; the single
 * role="status" live region carries the accessible loading announcement.
 */

import { Skeleton } from "@/components/ui/skeleton";

export function ValueStudioSkeletons() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading Value Studio">
      <span className="sr-only">Loading Value Studio…</span>
      <div aria-hidden="true" className="space-y-6">
        {/* Opportunity header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <Skeleton className="h-7 w-64" />
            <Skeleton className="h-4 w-96" />
          </div>
          <Skeleton className="h-9 w-72" />
        </div>
        {/* Journey strip */}
        <Skeleton className="h-16 w-full" />
        {/* Mission strip */}
        <Skeleton className="h-24 w-full" />
        {/* Impact row: three metrics + formula */}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
        {/* Main grid: content + 400px decision rail */}
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
          <div className="space-y-6">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-72 w-full" />
          </div>
          <Skeleton className="h-[560px]" />
        </div>
      </div>
    </div>
  );
}
