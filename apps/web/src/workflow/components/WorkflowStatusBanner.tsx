/**
 * WorkflowStatusBanner — Live harness run status for the AI Model page.
 *
 * Sources the most recent harness run (or a specific run by ID) and renders
 * a compact status banner showing: run status, current state/step, last-updated
 * timestamp, and gate/validation state if present.
 *
 * This is additive — it does not replace any existing page content.
 */

import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  ShieldAlert,
  XCircle,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useHarnessRun, useHarnessRuns } from "@/hooks/useHarness";
import type { HarnessRunStatus } from "@/api/harness";

// ── Status display config ─────────────────────────────────────────────────────

interface StatusConfig {
  label: string;
  icon: typeof CheckCircle2;
  className: string;
}

const STATUS_CONFIG: Record<HarnessRunStatus, StatusConfig> = {
  queued: {
    label: "Queued",
    icon: Clock,
    className: "bg-muted text-muted-foreground border-border",
  },
  running: {
    label: "Running",
    icon: Zap,
    className: "bg-blue-50 text-blue-700 border-blue-200",
  },
  waiting_for_human: {
    label: "Waiting for Review",
    icon: ShieldAlert,
    className: "bg-amber-50 text-amber-700 border-amber-200",
  },
  failed: {
    label: "Failed",
    icon: XCircle,
    className: "bg-red-50 text-red-700 border-red-200",
  },
  cancelled: {
    label: "Cancelled",
    icon: XCircle,
    className: "bg-muted text-muted-foreground border-border",
  },
  completed: {
    label: "Completed",
    icon: CheckCircle2,
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
};

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: HarnessRunStatus }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.queued;
  const Icon = cfg.icon;
  const isRunning = status === "running";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border",
        cfg.className,
      )}
    >
      <Icon className={cn("w-3 h-3 shrink-0", isRunning && "animate-pulse")} />
      {cfg.label}
    </span>
  );
}

// ── Inner banner (run data available) ────────────────────────────────────────

interface RunBannerProps {
  runId: string;
}

function RunBanner({ runId }: RunBannerProps) {
  const { data: run, isLoading, error } = useHarnessRun(runId);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground animate-pulse">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        Loading workflow status…
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
        Workflow status unavailable
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <StatusPill status={run.status} />
      <span className="text-xs text-muted-foreground font-mono">
        {run.current_state.replace(/_/g, " ")}
      </span>
      <span className="text-xs text-muted-foreground">
        Updated {formatRelative(run.updated_at)}
      </span>
      {run.trace_id && (
        <span className="text-[10px] text-muted-foreground/60 font-mono hidden sm:inline">
          {run.trace_id.slice(0, 8)}
        </span>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export interface WorkflowStatusBannerProps {
  /** Specific run ID to display. If omitted, falls back to the most recent run. */
  runId?: string;
  className?: string;
}

export function WorkflowStatusBanner({ runId, className }: WorkflowStatusBannerProps) {
  // If no runId provided, fetch the most recent run as fallback
  const { data: listData, isLoading: listLoading } = useHarnessRuns(
    runId ? undefined : { limit: 1 },
  );

  const resolvedRunId = runId ?? listData?.items[0]?.id;

  if (!runId && listLoading) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-muted/30 text-xs text-muted-foreground animate-pulse",
          className,
        )}
      >
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        Loading workflow status…
      </div>
    );
  }

  if (!resolvedRunId) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 px-4 py-2.5 rounded-lg border border-border bg-muted/30 text-xs text-muted-foreground",
          className,
        )}
      >
        <Clock className="w-3.5 h-3.5" />
        No active workflow run found
      </div>
    );
  }

  return (
    <div
      className={cn(
        "px-4 py-2.5 rounded-lg border border-border bg-muted/30",
        className,
      )}
      aria-label="Workflow status"
    >
      <RunBanner runId={resolvedRunId} />
    </div>
  );
}
