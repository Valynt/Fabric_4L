/**
 * usePaginatedList — Pagination State Management Hook
 *
 * UI/state-first pagination helper that manages page state, calculations,
 * and navigation methods. Designed to work with both server-side and
 * client-side pagination patterns.
 *
 * @example Server-side pagination
 * ```ts
 * const pagination = usePaginatedList({ mode: "server", totalItems: totalCount });
 * const query = useAccounts({ limit: pagination.limit, offset: pagination.offset });
 * ```
 *
 * @example Client-side pagination
 * ```ts
 * const pagination = usePaginatedList({ mode: "client", totalItems: allItems.length });
 * const paginatedItems = allItems.slice(pagination.offset, pagination.offset + pagination.limit);
 * ```
 */

import { useState, useMemo, useCallback } from "react";

export interface PaginatedListOptions {
  /** Initial page number (1-indexed) */
  initialPage?: number;
  /** Initial page size */
  initialPageSize?: number;
  /** Total number of items (required for client-side, optional for server-side) */
  totalItems?: number;
  /** Pagination mode: server-side (API-driven) or client-side (array slicing) */
  mode: "server" | "client";
}

export interface PaginatedListState {
  /** Current page number (1-indexed) */
  page: number;
  /** Number of items per page */
  pageSize: number;
  /** Offset for API queries (0-indexed) */
  offset: number;
  /** Limit for API queries */
  limit: number;
  /** Total number of pages */
  totalPages: number;
  /** Whether next page exists */
  canNext: boolean;
  /** Whether previous page exists */
  canPrevious: boolean;
  /** Navigate to next page */
  nextPage: () => void;
  /** Navigate to previous page */
  previousPage: () => void;
  /** Set specific page number */
  setPage: (page: number) => void;
  /** Set page size (resets to page 1) */
  setPageSize: (size: number) => void;
}

const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = 500;

export function usePaginatedList(options: PaginatedListOptions): PaginatedListState {
  const {
    initialPage = 1,
    initialPageSize = DEFAULT_PAGE_SIZE,
    totalItems = 0,
    mode,
  } = options;

  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  // Calculate derived values
  const offset = useMemo(() => (page - 1) * pageSize, [page, pageSize]);
  const limit = pageSize;

  const totalPages = useMemo(() => {
    if (mode === "client" && totalItems > 0) {
      return Math.ceil(totalItems / pageSize);
    }
    // For server-side, we don't know total pages without API response
    // Return 1 as minimum, caller can override if they have total count
    return Math.max(1, totalItems > 0 ? Math.ceil(totalItems / pageSize) : 1);
  }, [mode, totalItems, pageSize]);

  const canNext = useMemo(() => {
    if (mode === "client") {
      return page < totalPages;
    }
    // For server-side: if we know totalItems is 0, no next page
    // Otherwise assume there might be more pages unless we know otherwise
    if (totalItems === 0) return false;
    return page < totalPages;
  }, [mode, page, totalPages, totalItems]);

  const canPrevious = useMemo(() => page > 1, [page]);

  // Navigation methods
  const nextPage = useCallback(() => {
    if (canNext) {
      setPage((p) => p + 1);
    }
  }, [canNext]);

  const previousPage = useCallback(() => {
    if (canPrevious) {
      setPage((p) => p - 1);
    }
  }, [canPrevious]);

  const handleSetPage = useCallback((newPage: number) => {
    const clampedPage = Math.max(1, Math.min(newPage, totalPages));
    setPage(clampedPage);
  }, [totalPages]);

  const handleSetPageSize = useCallback((newSize: number) => {
    const clampedSize = Math.max(1, Math.min(newSize, MAX_PAGE_SIZE));
    setPageSize(clampedSize);
    setPage(1); // Reset to page 1 when changing page size
  }, []);

  return {
    page,
    pageSize,
    offset,
    limit,
    totalPages,
    canNext,
    canPrevious,
    nextPage,
    previousPage,
    setPage: handleSetPage,
    setPageSize: handleSetPageSize,
  };
}
