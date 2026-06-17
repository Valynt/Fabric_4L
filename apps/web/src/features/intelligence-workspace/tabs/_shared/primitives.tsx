/**
 * Shared presentational primitives for the core value-case workspace views.
 * Styling uses the app's semantic tokens so the screens match the rest of the UI.
 */
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

/** Normalise a 0–1 or 0–100 score to an integer percentage. */
export function toPercent(value?: number): number | null {
  if (value == null || Number.isNaN(value)) return null;
  const pct = value <= 1 ? value * 100 : value;
  return Math.round(Math.max(0, Math.min(100, pct)));
}

export function ScreenHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        <h2 className="vf-text-body-l font-semibold text-foreground">{title}</h2>
        {description && (
          <p className="mt-1 max-w-2xl vf-text-caption text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Tag({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 vf-text-micro font-medium",
        "bg-muted text-muted-foreground",
        className
      )}
    >
      {children}
    </span>
  );
}

export function ConfidenceBar({ value }: { value?: number }) {
  const pct = toPercent(value);
  if (pct == null) {
    return <span className="vf-text-micro text-muted-foreground">—</span>;
  }
  const color = pct >= 70 ? "bg-success" : pct >= 40 ? "bg-warning" : "bg-destructive";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="vf-text-micro text-muted-foreground">{pct}%</span>
    </div>
  );
}

/**
 * Rich empty state for a workspace view. Unlike a bare "no data" message this
 * explains the view's purpose and the next step in the value-case chain, so the
 * screen is useful even before any data exists.
 */
export function WorkspaceEmpty({
  icon: Icon,
  title,
  purpose,
  bullets,
  action,
}: {
  icon: LucideIcon;
  title: string;
  purpose: string;
  bullets?: string[];
  action?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-card/40 px-6 py-12">
      <div className="mx-auto flex max-w-md flex-col items-center text-center">
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Icon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </span>
        <h3 className="vf-text-body-s font-semibold text-foreground">{title}</h3>
        <p className="mt-1.5 vf-text-caption text-muted-foreground">{purpose}</p>
        {bullets && bullets.length > 0 && (
          <ul className="mt-4 space-y-1.5 text-left">
            {bullets.map((b) => (
              <li
                key={b}
                className="flex items-start gap-2 vf-text-caption text-muted-foreground"
              >
                <ArrowRight className="mt-0.5 h-3 w-3 shrink-0 text-primary" aria-hidden="true" />
                <span>{b}</span>
              </li>
            ))}
          </ul>
        )}
        {action && <div className="mt-5">{action}</div>}
      </div>
    </div>
  );
}

/** A slide-in detail panel rendered alongside list content. */
export function DetailPanel({
  eyebrow,
  title,
  onClose,
  footer,
  children,
}: {
  eyebrow?: string;
  title: string;
  onClose: () => void;
  footer?: ReactNode;
  children: ReactNode;
}) {
  return (
    <aside className="flex w-80 shrink-0 flex-col rounded-xl border border-border bg-card">
      <div className="flex items-start justify-between gap-2 border-b border-border p-4">
        <div>
          {eyebrow && (
            <p className="vf-text-micro font-medium uppercase tracking-wider text-muted-foreground">
              {eyebrow}
            </p>
          )}
          <h3 className="mt-0.5 vf-text-body-s font-semibold text-foreground">{title}</h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="vf-text-micro text-muted-foreground hover:text-foreground"
        >
          Close
        </button>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4">{children}</div>
      {footer && <div className="border-t border-border p-4">{footer}</div>}
    </aside>
  );
}
