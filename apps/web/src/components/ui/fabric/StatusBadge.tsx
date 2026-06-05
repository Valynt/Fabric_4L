import { Badge } from "@/components/ui/badge";
import { logWarn } from "@/lib/telemetry";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";

// ── StatusBadgeBlock types ───────────────────────────────────────────────────

export type BlockStatus =
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
  BlockStatus,
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
  status: BlockStatus;
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

// ── StatusBadge (legacy variant-based) ───────────────────────────────────────

export type StatusVariant = "default" | "secondary" | "outline" | "destructive" | "success" | "warning" | "info" | "pending";

/** Legacy status string values accepted by the `status` prop shorthand. */
export type LegacyStatusType =
  | "completed" | "created" | "queued" | "waiting_dependency" | "retrying"
  | "succeeded" | "success" | "running" | "processing" | "failed"
  | "failed_terminal" | "error" | "paused" | "interrupted" | "pending"
  | "cancelled" | "warning" | "info";

export interface StatusBadgeProps {
  /**
   * Render children directly with an explicit `variant`.
   * Mutually exclusive with `status`.
   */
  children?: ReactNode;
  variant?: StatusVariant;
  /**
   * Legacy shorthand: pass a status string and the badge renders the
   * appropriate label and variant automatically.
   * Migrated from WfPrimitives StatusBadge wrapper.
   */
  status?: LegacyStatusType | string;
  className?: string;
}

const STATUS_MAP: Record<string, { variant: StatusVariant; label: string }> = {
  completed:          { variant: "success",     label: "Completed" },
  created:            { variant: "secondary",   label: "Created" },
  queued:             { variant: "pending",     label: "Queued" },
  waiting_dependency: { variant: "pending",     label: "Waiting" },
  retrying:           { variant: "warning",     label: "Retrying" },
  succeeded:          { variant: "success",     label: "Succeeded" },
  success:            { variant: "success",     label: "Success" },
  running:            { variant: "warning",     label: "Running" },
  processing:         { variant: "warning",     label: "Processing" },
  failed:             { variant: "destructive", label: "Failed" },
  failed_terminal:    { variant: "destructive", label: "Failed" },
  error:              { variant: "destructive", label: "Error" },
  paused:             { variant: "secondary",   label: "Paused" },
  interrupted:        { variant: "secondary",   label: "Interrupted" },
  pending:            { variant: "pending",     label: "Pending" },
  cancelled:          { variant: "secondary",   label: "Cancelled" },
  warning:            { variant: "warning",     label: "Warning" },
  info:               { variant: "info",        label: "Info" },
};

const variantStyles: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-800 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300",
  warning: "bg-amber-100 text-amber-800 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-300",
  info: "bg-sky-100 text-sky-800 hover:bg-sky-100 dark:bg-sky-900/30 dark:text-sky-300",
  pending: "bg-orange-100 text-orange-800 hover:bg-orange-100 dark:bg-orange-900/30 dark:text-orange-300",
};

export function StatusBadge({ children, variant = "default", status, className }: StatusBadgeProps) {
  // `status` shorthand: resolve label and variant from the status map.
  // `status` takes precedence over `variant` — passing both is a misuse of the API.
  if (process.env.NODE_ENV !== "production" && status !== undefined && variant !== "default") {
    logWarn(
      `StatusBadge: \`variant="${variant}"\` is ignored when \`status\` is provided. ` +
        "Use either \`status\` or \`variant\`+\`children\`, not both."
    );
  }

  let resolvedVariant = variant;
  let resolvedChildren = children;
  if (status !== undefined) {
    const mapped = STATUS_MAP[status] ?? { variant: "default" as StatusVariant, label: status };
    resolvedVariant = mapped.variant;
    resolvedChildren = children ?? mapped.label;
  }

  const isCustom = resolvedVariant === "success" || resolvedVariant === "warning" || resolvedVariant === "info" || resolvedVariant === "pending";
  return (
    <Badge
      variant={isCustom ? "secondary" : resolvedVariant as "default" | "secondary" | "outline" | "destructive"}
      className={cn("vf-text-caption px-2 py-0.5 rounded-full font-medium", isCustom && variantStyles[resolvedVariant], className)}
    >
      {resolvedChildren}
    </Badge>
  );
}
