/**
 * component.tsx — Production component template
 *
 * Use this skeleton when converting prototype markup into a reusable,
 * design-governed component. It encodes the repo's frontend conventions:
 *   - Presentation separated from state (components receive data via props).
 *   - TanStack Query data fetched in hooks, never inside the component.
 *   - Design tokens from the theme (Tailwind v4 / shadcn semantic tokens),
 *     NOT page-local hex values.
 *   - Accessibility: semantic elements, keyboard nav, ARIA, focus management.
 *
 * Adapt the import paths and names; do NOT weaken the structure.
 */

import { useMemo } from "react";
import type { ReactNode } from "react";

// ── Domain model (view model, not the raw API DTO) ──────────────────────────
export interface WidgetProps {
  items: WidgetItem[];
  onSelect: (id: string) => void;
  isLoading?: boolean;
  emptyLabel?: ReactNode;
  /** Optional accessibility label describing the list's purpose. */
  ariaLabel?: string;
}

export interface WidgetItem {
  id: string;
  label: string;
  detail?: string;
}

/**
 * WidgetList — presentational list component.
 *
 * Pure presentation: all data and callbacks flow in via props so it can be
 * reused anywhere and tested in isolation. Fetching lives in a hook
 * (see templates/hook.ts).
 */
export function WidgetList({
  items,
  onSelect,
  isLoading = false,
  emptyLabel = "No items",
  ariaLabel = "Widget list",
}: WidgetProps) {
  const hasItems = items.length > 0;

  // Memoize derived values so we don't recompute on every render.
  const semantics = useMemo(() => {
    return {
      countLabel: `${items.length} item${items.length === 1 ? "" : "s"}`,
    };
  }, [items.length]);

  if (isLoading) {
    // Reuse the shared skeleton primitive — do not hand-roll spinners.
    return <div role="status" aria-live="polite">Loading…</div>;
  }

  if (!hasItems) {
    // Reuse the shared EmptyState primitive.
    return <div>{emptyLabel}</div>;
  }

  return (
    <ul aria-label={ariaLabel} className="flex flex-col gap-2">
      <li className="sr-only" aria-hidden="true">
        {semantics.countLabel}
      </li>
      {items.map((item) => (
        <li key={item.id}>
          <button
            type="button"
            onClick={() => onSelect(item.id)}
            aria-label={item.detail ? `${item.label} — ${item.detail}` : item.label}
          >
            <span>{item.label}</span>
            {item.detail ? (
              <span className="text-muted-foreground">{item.detail}</span>
            ) : null}
          </button>
        </li>
      ))}
    </ul>
  );
}
