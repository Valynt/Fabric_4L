/**
 * Formatting Utilities
 * 
 * Centralized date, currency, and number formatting functions.
 * Use these instead of defining inline format functions in components.
 * 
 * @example
 * ```tsx
 * import { formatDate, formatCurrency, formatRelativeTime } from '@/lib/formatters';
 * 
 * <span>{formatDate(createdAt)}</span>
 * <span>{formatCurrency(totalValue)}</span>
 * <span>{formatRelativeTime(updatedAt)}</span>
 * ```
 */

/**
 * Format a date string to locale date format
 * @param dateStr - ISO date string or undefined
 * @param fallback - Value to show if dateStr is undefined (default: "—")
 * @returns Formatted date string
 */
export function formatDate(dateStr: string | undefined, fallback = "—"): string {
  if (!dateStr) return fallback;
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * Format a date to relative time (e.g., "2h ago", "3d ago")
 * @param dateString - ISO date string
 * @returns Relative time string
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
}

// Compact USD currency formatter, built once at module scope; the locale and
// options are static, so constructing Intl.NumberFormat per call is wasteful.
const COMPACT_CURRENCY_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

/**
 * Format a number as currency (USD)
 * @param value - Number to format
 * @param fallback - Value to show if undefined/null (default: "—")
 * @returns Formatted currency string
 */
export function formatCurrency(value: number | undefined, fallback = "—"): string {
  if (value === undefined || value === null) return fallback;
  return COMPACT_CURRENCY_FORMATTER.format(value);
}

/**
 * Format cents to USD currency string
 * @param cents - Amount in cents
 * @returns Formatted USD string (e.g., "$12.34")
 */
export function formatCurrencyFromCents(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

/**
 * Format a number as compact currency (K/M/B)
 * @param value - Number to format
 * @returns Compact currency string (e.g., "$1.2M", "$850K")
 */
export function formatCompactCurrency(value: number): string {
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  } else if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  } else if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}K`;
  }
  return `$${value.toLocaleString()}`;
}

/**
 * Format a date as relative time with detailed granularity
 * Includes Today/Yesterday/Weeks ago patterns
 * @param dateStr - ISO date string
 * @param fallback - Value if undefined
 * @returns Human readable relative time
 */
export function formatDistanceToNow(dateStr: string | undefined, fallback = "—"): string {
  if (!dateStr) return fallback;
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return formatDate(dateStr);
}

/**
 * Truncate a string to max length with ellipsis
 * @param str - String to truncate
 * @param maxLength - Maximum length before truncation
 * @returns Truncated string
 */
export function truncateString(str: string | undefined, maxLength: number): string {
  if (!str || str.length <= maxLength) return str ?? '—';
  return `${str.slice(0, maxLength)}...`;
}
