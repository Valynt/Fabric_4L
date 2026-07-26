/**
 * GlobalSearchDialog Component
 *
 * Global search dialog using cmdk command palette with keyboard shortcut support.
 */

import { useEffect, useRef, useState } from "react";
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
  const openRef = useRef(open);
  openRef.current = open;
  const onOpenChangeRef = useRef(onOpenChange);
  onOpenChangeRef.current = onOpenChange;

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        onOpenChangeRef.current(true);
      }
      if (e.key === "Escape" && openRef.current) {
        onOpenChangeRef.current(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleClose = () => {
    setQuery("");
    clearSearch();
    onOpenChange(false);
  };

  const handleQueryChange = (value: string) => {
    setQuery(value);
    executeSearch(value);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      handleClose();
    } else {
      onOpenChange(true);
    }
  };

  const handleSelect = () => {
    handleClose();
  };

  const hasResults = data && Object.values(data.results).some((items) => items.length > 0);
  const showEmpty = !isLoading && !error && !hasResults;

  return (
    <CommandDialog open={open} onOpenChange={handleOpenChange}>
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
