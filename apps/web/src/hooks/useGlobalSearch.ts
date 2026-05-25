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

const SEARCH_QUERY_KEY = "global-search";

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
  debounceMs = 300,
}: UseGlobalSearchOptions = {}): UseGlobalSearchReturn {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, debounceMs);

  const searchRequest: SearchRequest = {
    q: debouncedQuery,
    scope: accountId ? "account" : "tenant",
    account_id: accountId,
    limit: 5, // Results per type
  };

  const { data, isLoading, error } = useQuery({
    queryKey: [SEARCH_QUERY_KEY, debouncedQuery, accountId],
    queryFn: () => search(searchRequest),
    enabled: enabled && debouncedQuery.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
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
    error: error as Error | null,
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
  const debouncedQuery = useDebounce(query, options.debounceMs || 300);

  const searchRequest: SearchRequest = {
    q: debouncedQuery,
    scope: options.accountId ? "account" : "tenant",
    account_id: options.accountId,
    types,
    limit: 10,
  };

  const { data, isLoading, error } = useQuery({
    queryKey: [SEARCH_QUERY_KEY, debouncedQuery, types, options.accountId],
    queryFn: () => search(searchRequest),
    enabled: options.enabled !== false && debouncedQuery.length > 0,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
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
    error: error as Error | null,
    search: handleSearch,
    clearSearch,
    query,
  };
}
