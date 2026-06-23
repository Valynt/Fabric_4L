/**
 * SearchResultsList Component
 *
 * Grouped search results display by entity type.
 */

import { SearchResultItem } from "./SearchResultItem";
import { getSearchResultTypeLabel } from "@/api/search";
import type { SearchResult, SearchResultType } from "./types";

interface SearchResultsListProps {
  results: Record<SearchResultType, SearchResult[]>;
  tenantSlug: string;
  onSelect?: () => void;
}

export function SearchResultsList({ results, tenantSlug, onSelect }: SearchResultsListProps) {
  const typeOrder: SearchResultType[] = [
    "account",
    "signal",
    "evidence",
    "value_case",
    "stakeholder",
    "value_driver",
    "formula",
    "benchmark",
    "value_pack",
    "graph_entity",
    "agent_thread",
    "workflow_run",
    "deliverable",
  ];

  const hasResults = Object.values(results).some((items) => items.length > 0);

  if (!hasResults) {
    return null;
  }

  return (
    <div className="py-2" data-testid="search-results">
      {typeOrder.map((type) => {
        const typeResults = results[type];
        if (!typeResults || typeResults.length === 0) {
          return null;
        }

        return (
          <div key={type} className="mb-4">
            <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {getSearchResultTypeLabel(type)} ({typeResults.length})
            </div>
            <div className="space-y-1">
              {typeResults.map((result) => (
                <SearchResultItem
                  key={`${result.type}-${result.id}`}
                  result={result}
                  tenantSlug={tenantSlug}
                  onSelect={onSelect}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
