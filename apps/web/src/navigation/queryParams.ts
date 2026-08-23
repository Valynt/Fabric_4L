/**
 * Query Parameter Utilities — Standardized URL State Management
 *
 * Provides Zod-backed serialization, deserialization, and safe merging
 * of query parameters for shareable view state.
 */

import { z } from "zod";

// ── Schemas ──────────────────────────────────────────────────────────────────

export const PaginationParams = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(25),
});

export const SortParams = z.object({
  sort: z.string().optional(),
});

export const DateRangeParams = z.object({
  from: z.iso.datetime().optional(),
  to: z.iso.datetime().optional(),
});

// ── Serialization ────────────────────────────────────────────────────────────

export function serializeQueryString(
  params: Record<string, string | number | boolean | undefined | string[]>
): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      searchParams.set(key, value.join(","));
    } else {
      searchParams.set(key, String(value));
    }
  }

  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

// ── Deserialization ──────────────────────────────────────────────────────────

export function parseQueryParams<T extends z.ZodTypeAny>(
  searchParams: URLSearchParams,
  schema: T
): z.infer<T> {
  const raw: Record<string, unknown> = {};
  searchParams.forEach((value, key) => {
    if (raw[key] !== undefined) {
      raw[key] = Array.isArray(raw[key])
        ? [...(raw[key] as string[]), value]
        : [raw[key], value];
    } else {
      raw[key] = value;
    }
  });
  return schema.parse(raw);
}

// ── Unknown param preservation ───────────────────────────────────────────────

/**
 * Merge new query params with existing, preserving unknown params.
 * Use when navigation should not strip params added by other features.
 */
export function mergeQueryParams(
  current: URLSearchParams,
  updates: Record<string, string | number | boolean | undefined | string[]>
): URLSearchParams {
  const merged = new URLSearchParams(current);

  for (const [key, value] of Object.entries(updates)) {
    if (value === undefined || value === null) {
      merged.delete(key);
    } else if (Array.isArray(value)) {
      merged.set(key, value.join(","));
    } else {
      merged.set(key, String(value));
    }
  }

  return merged;
}

