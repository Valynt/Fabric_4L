/**
 * Value Studio (mission-led) — mission status strip (contract §9.4, FE-MSN-*).
 *
 * Renders the mission projection: status (icon + text, never color-only),
 * coordination mode, autonomy summary, action progress as a segmented bar
 * with an accessible progressbar role, the distinct next-action and
 * needs-decision blocks, and Pause/Resume controls rendered ONLY when the
 * backend allowedActions list authorizes them (FE-MSN-006).
 */

import { AlertTriangle, Pause, Play } from "lucide-react";
import { Btn } from "@/components/ui/fabric/Btn";
import { StatusBadgeBlock, type BlockStatus } from "@/components/ui/fabric/StatusBadge";
import { cn } from "@/lib/utils";
import type { MissionProjection, MissionStatus } from "../types";
import { VALUE_STUDIO_ACTIONS } from "../types";
import {
  AUTONOMY_DISPLAY,
  COORDINATION_MODE_DISPLAY,
  MISSION_STATUS_DISPLAY,
} from "../viewModel";

export interface MissionStripProps {
  readonly mission: MissionProjection;
  readonly onPause: () => void;
  readonly onResume: () => void;
  readonly commandPending: boolean;
}

const STATUS_BADGE: Record<MissionStatus, BlockStatus> = {
  PLANNING: "queued",
  EXECUTING: "running",
  WAITING_FOR_HUMAN: "warning",
  PAUSING: "paused",
  PAUSED: "paused",
  RESUMING: "running",
  VERIFYING: "running",
  COMPLETED: "completed",
  MONITORING: "active",
  FAILED: "failed",
};

export function MissionStrip({ mission, onPause, onResume, commandPending }: MissionStripProps) {
  const canPause = mission.allowedActions.includes(VALUE_STUDIO_ACTIONS.missionPause);
  const canResume = mission.allowedActions.includes(VALUE_STUDIO_ACTIONS.missionResume);
  const progressText = `${mission.completedActionCount} of ${mission.totalActionCount} actions completed`;
  const needsDecision = mission.pendingDecisionCount > 0;

  return (
    <section
      aria-label={`Mission: ${mission.title}`}
      className="rounded-lg border border-border bg-card p-4 space-y-3"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <StatusBadgeBlock
          status={STATUS_BADGE[mission.status]}
          label={MISSION_STATUS_DISPLAY[mission.status]}
          size="sm"
        />
        <h2 className="vf-heading-m font-semibold text-foreground">{mission.title}</h2>
        <span className="vf-text-body-s text-muted-foreground">
          {COORDINATION_MODE_DISPLAY[mission.coordinationMode]} ·{" "}
          {AUTONOMY_DISPLAY[mission.autonomySummary]}
        </span>
        <span className="flex-1" />
        {canPause && (
          <Btn variant="outline" size="sm" onClick={onPause} disabled={commandPending}>
            <Pause className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Pause mission
          </Btn>
        )}
        {canResume && (
          <Btn variant="outline" size="sm" onClick={onResume} disabled={commandPending}>
            <Play className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Resume mission
          </Btn>
        )}
      </div>

      <div
        role="progressbar"
        aria-label="Mission action progress"
        aria-valuemin={0}
        aria-valuemax={mission.totalActionCount}
        aria-valuenow={mission.completedActionCount}
        aria-valuetext={progressText}
        className="flex items-center gap-2"
      >
        <div className="flex flex-1 gap-0.5" aria-hidden="true">
          {Array.from({ length: mission.totalActionCount }, (_, i) => (
            <span
              key={i}
              className={cn(
                "h-1.5 flex-1 rounded-full",
                i < mission.completedActionCount ? "bg-primary" : "bg-muted",
              )}
            />
          ))}
        </div>
        <span className="vf-text-body-s text-muted-foreground">{progressText}</span>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <div className="rounded-md bg-muted/50 px-3 py-2">
          <p className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
            Next action
          </p>
          <p className="vf-text-body-s text-foreground mt-0.5">
            {mission.nextAction ? mission.nextAction.title : "No queued action"}
          </p>
        </div>
        {needsDecision && (
          <div className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2">
            <p className="vf-text-caption font-medium uppercase tracking-wider text-warning flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" aria-hidden="true" />
              Needs your decision
            </p>
            <p className="vf-text-body-s text-foreground mt-0.5">
              {mission.pendingDecisionCount === 1
                ? "1 decision is waiting for you."
                : `${mission.pendingDecisionCount} decisions are waiting for you.`}
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
