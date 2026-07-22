import * as React from "react";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  MoreHorizontalIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from "@/components/ui/pagination";

// Constants
const MAX_VISIBLE_PAGES = 5;
const DEFAULT_PAGE_SIZE = 20;

// Common button styling for Previous/Next buttons (defined outside component to avoid recreation)
const NAV_BUTTON_CLASS_NAME = cn(
  "inline-flex items-center gap-1 h-8 px-2.5 rounded-md text-sm font-medium transition-colors",
  "hover:bg-accent hover:text-accent-foreground",
  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
);

export interface PaginationBarProps {
  /** Current page number (1-based) */
  page: number;
  /** Number of items per page */
  pageSize?: number;
  /** Total number of items (required for range variant) */
  totalItems?: number;
  /** Total number of pages (required for page variant) */
  totalPages?: number;
  /** Whether previous page is available */
  canPrevious?: boolean;
  /** Whether next page is available */
  canNext?: boolean;
  /** Callback when previous page is clicked */
  onPrevious?: () => void;
  /** Callback when next page is clicked */
  onNext?: () => void;
  /** Callback when a specific page is clicked */
  onPageChange?: (page: number) => void;
  /** Label for items (e.g., "accounts", "jobs") */
  itemLabel?: string;
  /** Summary display variant */
  summaryVariant?: "range" | "page";
  /** Additional class names */
  className?: string;
}

/**
 * PaginationBar - Standardized pagination wrapper around shadcn pagination
 * 
 * Provides consistent pagination UI across the application with two summary variants:
 * - "range": "Showing 1–25 of 143 accounts" (default for entity lists)
 * - "page": "Page 2 of 8" (for compact operational/admin tables)
 */
export function PaginationBar({
  page,
  pageSize = DEFAULT_PAGE_SIZE,
  totalItems,
  totalPages,
  canPrevious = true,
  canNext = true,
  onPrevious,
  onNext,
  onPageChange,
  itemLabel = "items",
  summaryVariant = "range",
  className,
}: PaginationBarProps) {
  // Validate props
  const safePage = Math.max(1, page);
  const safePageSize = Math.max(1, pageSize);
  const safeTotalItems = Math.max(0, totalItems ?? 0);

  // Calculate derived values
  const calculatedTotalPages = totalPages || (safeTotalItems > 0 ? Math.ceil(safeTotalItems / safePageSize) : 1);
  const clampedPage = Math.min(safePage, calculatedTotalPages);
  const startIndex = (clampedPage - 1) * safePageSize + 1;
  const endIndex = Math.min(clampedPage * safePageSize, safeTotalItems);

  // Render summary text based on variant
  const renderSummary = () => {
    if (summaryVariant === "page") {
      return (
        <span className="vf-text-body-s text-muted-foreground">
          Page {clampedPage} of {calculatedTotalPages}
        </span>
      );
    }

    // range variant
    if (safeTotalItems > 0) {
      return (
        <span className="vf-text-body-s text-muted-foreground">
          Showing {startIndex}–{endIndex} of {safeTotalItems} {itemLabel}
        </span>
      );
    }

    return null;
  };

  // Generate page numbers for display (show current, first, last, and neighbors)
  const generatePageNumbers = () => {
    const pages: (number | string)[] = [];

    if (calculatedTotalPages <= MAX_VISIBLE_PAGES) {
      return Array.from({ length: calculatedTotalPages }, (_, i) => i + 1);
    }

    pages.push(1);

    if (clampedPage > 3) {
      pages.push("...");
    }

    const start = Math.max(2, clampedPage - 1);
    const end = Math.min(calculatedTotalPages - 1, clampedPage + 1);

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (clampedPage < calculatedTotalPages - 2) {
      pages.push("...");
    }

    pages.push(calculatedTotalPages);

    return pages;
  };

  const pageNumbers = generatePageNumbers();

  return (
    <div className={cn("flex items-center justify-between px-4 py-3 border-t border-border", className)}>
      {/* Summary */}
      {renderSummary()}

      {/* Pagination Controls */}
      <Pagination className="w-auto">
        <PaginationContent className="flex items-center gap-1">
          <PaginationItem>
            <button type="button"
              onClick={onPrevious}
              disabled={!canPrevious}
              className={cn(
                NAV_BUTTON_CLASS_NAME,
                !canPrevious && "opacity-50 cursor-not-allowed pointer-events-none"
              )}
              aria-label="Go to previous page"
            >
              <ChevronLeftIcon size={14} />
              <span className="hidden sm:inline">Previous</span>
            </button>
          </PaginationItem>

          {pageNumbers.map((p, index) => (
            <React.Fragment key={typeof p === 'number' ? p : `ellipsis-${index}`}>
              {p === "..." ? (
                <PaginationItem>
                  <PaginationEllipsis>
                    <MoreHorizontalIcon size={14} />
                  </PaginationEllipsis>
                </PaginationItem>
              ) : (
                <PaginationItem>
                  <PaginationLink
                    isActive={p === clampedPage}
                    onClick={() => onPageChange?.(p as number)}
                    className="h-8 w-8"
                  >
                    {p}
                  </PaginationLink>
                </PaginationItem>
              )}
            </React.Fragment>
          ))}

          <PaginationItem>
            <button type="button"
              onClick={onNext}
              disabled={!canNext}
              className={cn(
                NAV_BUTTON_CLASS_NAME,
                !canNext && "opacity-50 cursor-not-allowed pointer-events-none"
              )}
              aria-label="Go to next page"
            >
              <span className="hidden sm:inline">Next</span>
              <ChevronRightIcon size={14} />
            </button>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  );
}
