/**
 * api-adapter.ts — DTO → domain mapper at the network boundary
 *
 * Per the repo's frontend rules: components consume domain/view models, NOT raw
 * API DTOs. This adapter is the single place where a wire response becomes the
 * shape the UI actually uses. Keeping it isolated means a backend contract
 * change touches exactly one file, and components never leak snake_case or
 * server fields into the view layer.
 *
 * Use with templates/hook.ts: the hook calls schema.parse() at the boundary,
 * then this adapter maps the typed DTO to the domain model.
 */

import { z } from "zod";

// ── 1. Wire schema (server shape — snake_case, optional fields, defaults) ────
export const WidgetDtoSchema = z
  .object({
    id: z.string(),
    display_name: z.string(),
    status: z.string().default("active"),
    created_by: z.string().nullable().optional(),
    updated_at: z.string().optional(),
    // server may add fields; tolerate forward-compatible additions
  })
  .passthrough();

export type WidgetDto = z.infer<typeof WidgetDtoSchema>;

// ── 2. Domain / view model (no server fields leak into the UI) ───────────────
export interface Widget {
  id: string;
  name: string;
  status: WidgetStatus;
  updatedAt?: string;
}

export type WidgetStatus = "active" | "archived" | "paused";

// ── 3. Adapter function (pure, unit-testable) ────────────────────────────────
// Maps every domain field explicitly. Do NOT spread the DTO — an explicit map
// is what prevents accidental server-shape leakage and nulls slipping through.
export function toWidget(dto: WidgetDto): Widget {
  return {
    id: dto.id,
    name: dto.display_name,
    status: toWidgetStatus(dto.status),
    updatedAt: dto.updated_at,
  };
}

// Normalize loose server status strings to the closed domain union.
// Fail closed: unknown status maps to a safe default, never throws in the UI.
function toWidgetStatus(raw: string): WidgetStatus {
  switch (raw.toLowerCase()) {
    case "active":
      return "active";
    case "archived":
      return "archived";
    case "paused":
      return "paused";
    default:
      return "active";
  }
}

// ── 4. Collection adapter (with null-safe filtering) ─────────────────────────
export function toWidgetList(dtos: WidgetDto[]): Widget[] {
  return dtos
    .map((dto) => {
      // Reject malformed rows (missing identity) instead of returning them.
      if (!dto.id) return null;
      return toWidget(dto);
    })
    .filter((w): w is Widget => w !== null);
}
