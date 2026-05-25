/**
 * useGlobalSearch Hook
 *
 * React hook for global search functionality with TanStack Query integration.
 */

import { useState, useCallback, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { search } from "@/api/search";
import type {
  SearchRequest,
  SearchResponse,
  SearchResultType,
} from "@/components/search/types";

interface UseGlobalSearchOptions {
  tenantSlug?: string;
  accountId?: string;
  enabled?: boolean;
  debounceMs?: number;
}

interface UseGlobalSearchReturn {
  data: SearchResponse | undefined;
  isLoading: boolean;
  error: Error | null;
  search: (query: string) => void;
  clearSearch: () => void;
  query: string;
}

// Constants for search configuration
const SEARCH_QUERY_KEY = "global-search";
const DEFAULT_DEBOUNCE_MS = 300;
const DEFAULT_RESULTS_LIMIT = 5;
const DEFAULT_TYPED_RESULTS_LIMIT = 10;
const SEARCH_STALE_TIME_MS = 5 * 60 * 1000; // 5 minutes
const SEARCH_GC_TIME_MS = 10 * 60 * 1000; // 10 minutes

/**
 * Simple debounce hook implementation
 */
function useDebounce(value: string, delay: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook for global search with debouncing and caching
 */
export function useGlobalSearch({
  tenantSlug,
  accountId,
  enabled = true,
  debounceMs = DEFAULT_DEBOUNCE_MS,
}: UseGlobalSearchOptions = {}): UseGlobalSearchReturn {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, debounceMs);

  const searchRequest: SearchRequest = {
    q: debouncedQuery,
    scope: accountId ? "account" : "tenant",
    account_id: accountId,
    limit: DEFAULT_RESULTS_LIMIT,
  };

  const { data, isLoading, error } = useQuery({
    queryKey: [SEARCH_QUERY_KEY, debouncedQuery, accountId],
    queryFn: () => search(searchRequest),
    enabled: enabled && debouncedQuery.length > 0,
    staleTime: SEARCH_STALE_TIME_MS,
    gcTime: SEARCH_GC_TIME_MS,
  });

  const handleSearch = useCallback((newQuery: string) => {
    setQuery(newQuery);
  }, []);

  const clearSearch = useCallback(() => {
    setQuery("");
  }, []);

  return {
    data,
    isLoading,
    error: error instanceof Error ? error : (error ? new Error(String(error)) : null),
    search: handleSearch,
    clearSearch,
    query,
  };
}

/**
 * Hook for searching specific entity types
 */
export function useTypedSearch(
  types: SearchResultType[],
  options: UseGlobalSearchOptions = {}
): UseGlobalSearchReturn {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, options.debounceMs || DEFAULT_DEBOUNCE_MS);

  const searchRequest: SearchRequest = {
    q: debouncedQuery,
    scope: options.accountId ? "account" : "tenant",
    account_id: options.accountId,
    types,
    limit: DEFAULT_TYPED_RESULTS_LIMIT,
  };

  const { data, isLoading, error } = useQuery({
    queryKey: [SEARCH_QUERY_KEY, debouncedQuery, types, options.accountId],
    queryFn: () => search(searchRequest),
    enabled: options.enabled !== false && debouncedQuery.length > 0,
    staleTime: SEARCH_STALE_TIME_MS,
    gcTime: SEARCH_GC_TIME_MS,
  });

  const handleSearch = useCallback((newQuery: string) => {
    setQuery(newQuery);
  }, []);

  const clearSearch = useCallback(() => {
    setQuery("");
  }, []);

  return {
    data,
    isLoading,
    error: error instanceof Error ? error : (error ? new Error(String(error)) : null),
    search: handleSearch,
    clearSearch,
    query,
  };
}
