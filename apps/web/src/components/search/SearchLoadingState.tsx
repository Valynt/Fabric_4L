/**
 * SearchLoadingState Component
 *
 * Loading skeleton for search results.
 */

export function SearchLoadingState() {
  return (
    <div className="py-4 px-2 space-y-3" data-testid="search-loading">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="w-4 h-4 rounded bg-muted animate-pulse flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
            <div className="h-3 w-1/2 rounded bg-muted animate-pulse" />
            <div className="h-3 w-full rounded bg-muted animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}
