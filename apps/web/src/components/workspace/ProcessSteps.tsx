/**
 * ProcessSteps — Visual step progression for agent runs.
 *
 * Renders the AG-UI step lifecycle as a compact vertical list with
 * status icons (done/active/pending/error/skipped). This is the
 * production version of the prototype's `ProcessStep` component
 * from AgentMockup.tsx, enhanced with:
 *   - Full AG-UI StepStatus support (5 states vs. prototype's 3)
 *   - Collapsible wrapper with step count summary
 *   - Elapsed time display for completed steps
 *   - Error state with red icon
 *   - Smooth transitions between states
 *
 * UI Contract (Data):
 *   - `steps` : array of StepSnapshot objects from useAgentEvents
 *   - Each step has: id, label, status, startedAt?, finishedAt?
 *
 * UI Contract (Behavior):
 *   - Renders nothing when `steps` is empty
 *   - Auto-collapses when all steps are "done" (run complete)
 *   - Clicking the header toggles collapsed/expanded
 *
 * UI Contract (Rendering):
 *   - Compact card with muted background (matches prototype style)
 *   - Status icons: ✓ emerald (done), ⟳ spinning primary (active),
 *     ○ muted (pending), ✕ destructive (error), ⊘ muted (skipped)
 *   - Active step label is primary-coloured and bold
 *   - Pending steps are dimmed
 */

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  MinusCircle,
  ChevronDown,
} from "lucide-react";

import type { StepSnapshot, StepStatus } from "@/agui/events";

/** Delay before auto-collapsing the step list after all steps complete (ms) */
const AUTOCOLLAPSE_DELAY_MS = 1500;

// ── Status Icon Map ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  StepStatus,
  { icon: typeof CheckCircle2; className: string; labelClass: string; animate?: boolean }
> = {
  done: {
    icon: CheckCircle2,
    className: "text-success",
    labelClass: "text-foreground",
  },
  active: {
    icon: Loader2,
    className: "text-primary",
    labelClass: "text-primary font-medium",
    animate: true,
  },
  pending: {
    icon: Circle,
    className: "text-muted-foreground/40",
    labelClass: "text-muted-foreground/50",
  },
  error: {
    icon: XCircle,
    className: "text-destructive",
    labelClass: "text-destructive",
  },
  skipped: {
    icon: MinusCircle,
    className: "text-muted-foreground/40",
    labelClass: "text-muted-foreground/50 line-through",
  },
};

// ── Step Row ────────────────────────────────────────────────────────────────

function StepRow({ step }: { step: StepSnapshot }) {
  const config = STATUS_CONFIG[step.status];
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-2 py-1">
      <Icon
        className={cn(
          "w-3.5 h-3.5 shrink-0",
          config.className,
          config.animate && "animate-spin",
        )}
      />
      <span className={cn("text-xs", config.labelClass)}>{step.label}</span>
    </div>
  );
}

// ── ProcessSteps ────────────────────────────────────────────────────────────

export interface ProcessStepsProps {
  /** Step snapshots from useAgentEvents */
  steps: StepSnapshot[];
  /** Additional wrapper classes */
  className?: string;
}

export function ProcessSteps({ steps, className }: ProcessStepsProps) {
  const [collapsed, setCollapsed] = useState(false);

  // Auto-collapse when all steps are done
  const allDone = steps.length > 0 && steps.every((s) => s.status === "done" || s.status === "skipped");
  const hasError = steps.some((s) => s.status === "error");
  const activeCount = steps.filter((s) => s.status === "active").length;
  const doneCount = steps.filter((s) => s.status === "done").length;

  useEffect(() => {
    if (allDone && !hasError) {
      // Auto-collapse after a short delay so the user sees the final state
      const timer = setTimeout(() => setCollapsed(true), AUTOCOLLAPSE_DELAY_MS);
      return () => clearTimeout(timer);
    }

    return undefined;
  }, [allDone, hasError]);

  // Don't render if there are no steps
  if (steps.length === 0) return null;

  return (
    <div className={cn("bg-muted/60 rounded-lg border border-border/60 overflow-hidden", className)}>
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-muted/80 transition-colors"
        aria-expanded={!collapsed}
      >
        <div className="flex items-center gap-2">
          <span className="vf-text-caption font-semibold text-foreground">
            {hasError
              ? "Processing failed"
              : allDone
                ? "Processing complete"
                : activeCount > 0
                  ? "Processing…"
                  : "Queued"}
          </span>
          <span className="vf-text-micro text-muted-foreground">
            {doneCount}/{steps.length} steps
          </span>
        </div>
        <ChevronDown
          className={cn(
            "w-3.5 h-3.5 text-muted-foreground transition-transform",
            collapsed && "-rotate-90",
          )}
        />
      </button>

      {/* Step list */}
      {!collapsed && (
        <div className="px-3 pb-2.5 space-y-0.5">
          {steps.map((step) => (
            <StepRow key={step.id} step={step} />
          ))}
        </div>
      )}
    </div>
  );
}

export default ProcessSteps;
