/**
 * StatusBadge — Semantic status indicator with built-in icon and colour mapping.
 *
 * UI Contract (Data):
 *   - `status` : one of 11 semantic statuses (connected, active, warning, error, …)
 *   - `label`  : optional override for the display text (defaults to status label)
 *   - `size`   : "sm" (inline) or "md" (standard)
 *
 * UI Contract (Rendering):
 *   - Each status maps to a deterministic icon + colour pair
 *   - Unknown statuses render nothing (fail-safe)
 *   - Pill-shaped with icon + text, never wraps
 *
 * Note: This is distinct from `ui/fabric/StatusBadge` which wraps shadcn Badge
 * with string-based variants. This component is self-contained with built-in
 * icons and is designed for operational dashboards and agent workflow steps.
 *
 * Extracted from: _ui-prototype/app/src/components/blocks/status-badge.tsx
 */
import { cn } from "@/lib/utils";
import { CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";

export type Status =
  | "connected"
  | "active"
  | "warning"
  | "error"
  | "paused"
  | "completed"
  | "queued"
  | "running"
  | "failed"
  | "degraded"
  | "healthy";

const statusConfig: Record<
  Status,
  { icon: typeof CheckCircle2; classes: string; label: string }
> = {
  connected:  { icon: CheckCircle2,  classes: "bg-emerald-500/10 text-emerald-500", label: "Connected" },
  healthy:    { icon: CheckCircle2,  classes: "bg-emerald-500/10 text-emerald-500", label: "Healthy" },
  active:     { icon: CheckCircle2,  classes: "bg-emerald-500/10 text-emerald-500", label: "Active" },
  completed:  { icon: CheckCircle2,  classes: "bg-emerald-500/10 text-emerald-500", label: "Completed" },
  warning:    { icon: AlertTriangle, classes: "bg-amber-500/10 text-amber-500",     label: "Delayed" },
  degraded:   { icon: AlertTriangle, classes: "bg-amber-500/10 text-amber-500",     label: "Degraded" },
  error:      { icon: XCircle,       classes: "bg-destructive/10 text-destructive",  label: "Failed" },
  failed:     { icon: XCircle,       classes: "bg-destructive/10 text-destructive",  label: "Failed" },
  paused:     { icon: Clock,         classes: "bg-muted text-muted-foreground",      label: "Paused" },
  queued:     { icon: Clock,         classes: "bg-muted text-muted-foreground",      label: "Queued" },
  running:    { icon: Clock,         classes: "bg-primary/10 text-primary",          label: "Running" },
};

export interface StatusBadgeBlockProps {
  /** Semantic status key */
  status: Status;
  /** Override display label */
  label?: string;
  /** Additional classes */
  className?: string;
  /** Badge size */
  size?: "sm" | "md";
}

export function StatusBadgeBlock({
  status,
  label,
  className,
  size = "md",
}: StatusBadgeBlockProps) {
  const config = statusConfig[status];
  if (!config) return null;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        size === "sm" ? "text-xs px-2 py-0.5" : "text-xs px-2.5 py-1",
        config.classes,
        className,
      )}
    >
      <Icon className={size === "sm" ? "w-2.5 h-2.5" : "w-3 h-3"} />
      {label ?? config.label}
    </span>
  );
}
