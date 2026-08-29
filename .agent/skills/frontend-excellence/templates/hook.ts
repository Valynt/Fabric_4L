/**
 * hook.ts — Typed TanStack Query hook + Zod parser template
 *
 * The canonical data-fetching pattern for this repo:
 *   1. A Zod schema validates/normalizes the raw API DTO (network boundary).
 *   2. An adapter maps the validated DTO → a domain/view model.
 *   3. TanStack Query owns caching, staleness, and refetch.
 *   4. Query keys come from the centralized registry (apps/web/src/hooks/queryKeys).
 *
 * Follow the repo conventions: apiGet/apiPost from `@/api/typedClient`,
 * QK keys from `./queryKeys`, STALE_TIME / POLL_INTERVALS from `./useApiShared`
 * and `./usePolling`. Register your query key factory in queryKeys.ts.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiGet, apiPost } from "@/api/typedClient";
import { QK } from "./queryKeys";
import { STALE_TIME } from "./useApiShared";

// ── 1. Wire schema: validates the API response at the boundary ───────────────
// Reflect the actual server shape. Unknown fields are tolerated (passthrough)
// so a forward-compatible server never breaks the client.
const WidgetItemSchema = z
  .object({
    id: z.string().min(1),
    title: z.string().min(1),
    status: z.string().default("active"),
    updated_at: z.string().optional(),
  })
  .passthrough();

const WidgetListSchema = z
  .object({
    items: z.array(WidgetItemSchema).default([]),
    total: z.number().default(0),
    has_more: z.boolean().default(false),
  })
  .passthrough();

// ── 2. Domain model (view shape, snake→camel where appropriate) ──────────────
export interface Widget {
  id: string;
  title: string;
  status: string;
  updatedAt?: string;
}

// ── 3. Adapter: DTO → domain. Fail closed on missing identity. ───────────────
function toWidget(dto: z.infer<typeof WidgetItemSchema>): Widget | null {
  const id = String(dto.id ?? "").trim();
  if (!id) return null; // never emit an identity-less widget
  return {
    id,
    title: dto.title,
    status: dto.status,
    updatedAt: dto.updated_at,
  };
}

function parseList(data: unknown): { items: Widget[]; total: number; hasMore: boolean } {
  const parsed = WidgetListSchema.parse(data);
  const items = parsed.items
    .map(toWidget)
    .filter((w): w is Widget => w !== null);
  return { items, total: parsed.total, hasMore: parsed.has_more };
}

// ── 4. Query hook ────────────────────────────────────────────────────────────
export function useWidgets(options: { limit?: number } = {}) {
  const { limit = 50 } = options;
  return useQuery({
    queryKey: [...QK.widgets.list({ limit })], // add the factory in queryKeys.ts
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      const res = await apiGet<unknown>("l4", `/widgets?${params.toString()}`);
      return parseList(res.data);
    },
    staleTime: STALE_TIME.stats,
  });
}

// ── 5. Mutation hook ─────────────────────────────────────────────────────────
export function useCreateWidget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { title: string }) => {
      const res = await apiPost<unknown>("l4", "/widgets", input);
      return toWidget(WidgetItemSchema.parse(res.data));
    },
    onSuccess: () => {
      queryClient
        .invalidateQueries({ queryKey: QK.widgets.all })
        .catch(() => undefined);
    },
  });
}
