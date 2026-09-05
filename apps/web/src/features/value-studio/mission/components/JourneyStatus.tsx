/**
 * Value Studio (mission-led) — opportunity journey status (contract §9.3, FE-JNY-*).
 *
 * Status strip, not navigation: an ordered list of the seven canonical stages
 * with server-supplied state. The current stage carries aria-current="step"
 * and every item includes sr-only position text ("Stage 5 of 7: Review —
 * current") so position is never conveyed by color alone (FE-A11Y-004).
 */

import { CheckCircle2, Circle, CircleDot, OctagonAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import type { JourneyProjection, JourneyStageState } from "../types";
import { JOURNEY_STAGE_DISPLAY } from "../viewModel";

export interface JourneyStatusProps {
  readonly journey: JourneyProjection;
}

const STATE_ICON: Record<JourneyStageState, typeof Circle> = {
  completed: CheckCircle2,
  current: CircleDot,
  upcoming: Circle,
  blocked: OctagonAlert,
};

const STATE_TEXT: Record<JourneyStageState, string> = {
  completed: "completed",
  current: "current stage",
  upcoming: "upcoming",
  blocked: "blocked",
};

export function JourneyStatus({ journey }: JourneyStatusProps) {
  const total = journey.stages.length;
  return (
    <nav aria-label="Opportunity journey status" className="w-full">
      <ol className="flex flex-wrap items-center gap-y-2">
        {journey.stages.map((stage, index) => {
          const Icon = STATE_ICON[stage.state];
          return (
            <li
              key={stage.stage}
              aria-current={stage.state === "current" ? "step" : undefined}
              className="flex items-center"
            >
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 vf-text-body-s",
                  stage.state === "current" && "font-semibold text-foreground",
                  stage.state === "completed" && "text-success",
                  stage.state === "upcoming" && "text-muted-foreground",
                  stage.state === "blocked" && "text-destructive",
                )}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span aria-hidden="true">{JOURNEY_STAGE_DISPLAY[stage.stage]}</span>
                <span className="sr-only">
                  {`Stage ${index + 1} of ${total}: ${JOURNEY_STAGE_DISPLAY[stage.stage]} — ${STATE_TEXT[stage.state]}`}
                  {stage.detail ? `. ${stage.detail}` : ""}
                </span>
              </span>
              {index < total - 1 && (
                <span className="mx-2 h-px w-6 bg-border" aria-hidden="true" />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
