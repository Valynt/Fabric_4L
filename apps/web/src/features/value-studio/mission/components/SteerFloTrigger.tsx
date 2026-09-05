/**
 * Value Studio (mission-led) — Steer Flo entry point (contract §9.13, FE-STEER-*).
 *
 * Renders only when the mission projection's allowedActions contains
 * `mission.steer`; the front end never infers this permission. Opens the
 * advisory Steer Flo panel (Slice 1: read-only guidance; natural-language
 * steering lands in Phase 2).
 */

import { MessageSquareText } from "lucide-react";
import { Btn } from "@/components/ui/fabric/Btn";
import type { MissionProjection } from "../types";
import { VALUE_STUDIO_ACTIONS } from "../types";

export interface SteerFloTriggerProps {
  readonly mission: MissionProjection;
  readonly onOpen: () => void;
}

export function SteerFloTrigger({ mission, onOpen }: SteerFloTriggerProps) {
  if (!mission.allowedActions.includes(VALUE_STUDIO_ACTIONS.steerFlo)) {
    return null;
  }
  return (
    <Btn variant="outline" size="sm" onClick={onOpen} aria-label="Open Steer Flo panel">
      <MessageSquareText className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
      Steer Flo
    </Btn>
  );
}
