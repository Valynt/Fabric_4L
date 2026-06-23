/**
 * GlobalSearchDialog Component
 *
 * Global search dialog using cmdk command palette with keyboard shortcut support.
 */

import { useEffect, useState } from "react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
} from "@/components/ui/command";
import { useGlobalSearch } from "@/hooks/useGlobalSearch";
import { SearchResultsList } from "./SearchResultsList";
import { SearchEmptyState } from "./SearchEmptyState";
import { SearchLoadingState } from "./SearchLoadingState";
import { SearchErrorState } from "./SearchErrorState";
import type { GlobalSearchDialogProps } from "./types";

export function GlobalSearchDialog({
  open,
  onOpenChange,
  tenantSlug,
  accountId,
}: GlobalSearchDialogProps) {
  const [query, setQuery] = useState("");
  
  // Disable search if tenantSlug is not available
  const { data, isLoading, error, search: executeSearch, clearSearch } = useGlobalSearch({
    tenantSlug,
    accountId,
    enabled: !!tenantSlug,
  });

  // Handle keyboard shortcut - Cmd/Ctrl+K to open, Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onOpenChange(true);
      }
      if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onOpenChange]);

  // Clear search when dialog closes
  useEffect(() => {
    if (!open) {
      setQuery("");
      clearSearch();
    }
  }, [open, clearSearch]);

  const handleQueryChange = (value: string) => {
    setQuery(value);
    executeSearch(value);
  };

  const handleSelect = () => {
    onOpenChange(false);
  };

  const hasResults = data && Object.values(data.results).some((items) => items.length > 0);
  const showEmpty = !isLoading && !error && !hasResults;

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        placeholder="Search accounts, signals, evidence..."
        value={query}
        onValueChange={handleQueryChange}
      />
      <CommandList>
        {isLoading && <SearchLoadingState />}
        
        {error && (
          <SearchErrorState 
            error={error} 
            onRetry={() => executeSearch(query)}
          />
        )}
        
        {showEmpty && <SearchEmptyState query={query} />}
        
        {hasResults && data && tenantSlug && (
          <SearchResultsList
            results={data.results}
            tenantSlug={tenantSlug}
            onSelect={handleSelect}
          />
        )}
      </CommandList>
    </CommandDialog>
  );
}
