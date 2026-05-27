import { cn } from "@/lib/utils";
import { CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";

export type Status = "connected" | "active" | "warning" | "error" | "paused" | "completed" | "queued" | "running" | "failed" | "degraded" | "healthy";

const statusConfig: Record<Status, { icon: typeof CheckCircle2; classes: string; label: string }> = {
  connected: { icon: CheckCircle2, classes: "bg-emerald-500/10 text-emerald-500", label: "Connected" },
  healthy: { icon: CheckCircle2, classes: "bg-emerald-500/10 text-emerald-500", label: "Healthy" },
  active: { icon: CheckCircle2, classes: "bg-emerald-500/10 text-emerald-500", label: "Active" },
  completed: { icon: CheckCircle2, classes: "bg-emerald-500/10 text-emerald-500", label: "Completed" },
  warning: { icon: AlertTriangle, classes: "bg-amber-500/10 text-amber-500", label: "Delayed" },
  degraded: { icon: AlertTriangle, classes: "bg-amber-500/10 text-amber-500", label: "Degraded" },
  error: { icon: XCircle, classes: "bg-destructive/10 text-destructive", label: "Failed" },
  failed: { icon: XCircle, classes: "bg-destructive/10 text-destructive", label: "Failed" },
  paused: { icon: Clock, classes: "bg-muted text-muted-foreground", label: "Paused" },
  queued: { icon: Clock, classes: "bg-muted text-muted-foreground", label: "Queued" },
  running: { icon: Clock, classes: "bg-primary/10 text-primary", label: "Running" },
};

interface StatusBadgeProps {
  status: Status;
  label?: string;
  className?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, label, className, size = "md" }: StatusBadgeProps) {
  const config = statusConfig[status];
  if (!config) return null;
  const Icon = config.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        size === "sm" ? "text-[10px] px-2 py-0.5" : "text-xs px-2.5 py-1",
        config.classes,
        className
      )}
    >
      <Icon className={size === "sm" ? "w-2.5 h-2.5" : "w-3 h-3"} />
      {label ?? config.label}
    </span>
  );
}
