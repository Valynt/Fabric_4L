/**
 * SearchEmptyState Component
 *
 * Empty state UI when no search results are found.
 */

import { Search } from "lucide-react";

interface SearchEmptyStateProps {
  query?: string;
}

export function SearchEmptyState({ query }: SearchEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
        <Search className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-medium mb-2">
        {query ? "No results found" : "Search for anything"}
      </h3>
      <p className="text-xs text-muted-foreground max-w-sm">
        {query
          ? `We couldn't find any results for "${query}". Try a different search term or check your spelling.`
          : "Start typing to search across accounts, signals, evidence, and more."}
      </p>
    </div>
  );
}
