/**
 * Query Parameter Utilities — Standardized URL State Management
 *
 * Provides Zod-backed serialization, deserialization, and safe merging
 * of query parameters for shareable view state.
 */

import { useSearchParams } from "react-router-dom";
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

export const SignalFilterParams = z.object({
  status: z.string().optional(),
  confidence_gte: z.coerce.number().min(0).max(1).optional(),
  source: z.string().optional(),
  persona: z.string().optional(),
  q: z.string().optional(),
  ...PaginationParams.shape,
  ...SortParams.shape,
  ...DateRangeParams.shape,
});

export const PanelParams = z.object({
  panel: z.enum(["detail", "agent", "none"]).optional(),
  entity: z.string().optional(),
  thread: z.string().optional(),
});

export const ValuePilotParams = z.object({
  mode: z.literal("value-pilot").optional(),
  step: z.coerce.number().int().min(0).max(6).optional(),
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

// ── Safe array parsing ───────────────────────────────────────────────────────

export function parseCommaSeparated(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
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

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useFabricQueryParams<T extends z.ZodTypeAny>(schema: T) {
  const [searchParams, setSearchParams] = useSearchParams();
  const parsed = parseQueryParams(searchParams, schema);

  const update = (
    updates: Partial<
      Record<string, string | number | boolean | undefined | string[]>
    >
  ) => {
    const merged = mergeQueryParams(searchParams, updates);
    setSearchParams(merged, { replace: true });
  };

  return { params: parsed, searchParams, update };
}
