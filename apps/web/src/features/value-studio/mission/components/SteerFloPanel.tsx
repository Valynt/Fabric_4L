/**
 * Value Studio (mission-led) — Steer Flo panel (contract §9.13, FE-STEER-*).
 *
 * Slice 1 renders the advisory surface only: a disclaimer that steering is
 * advisory, that Flo may decline requests outside policy, and that no
 * economic value changes without a human-governed decision. The instruction
 * composer is visibly disabled until the Phase-2 command backend lands — no
 * fake submission path.
 */

import { SidePanel } from "@/components/ui/fabric/SidePanel";
import { Textarea } from "@/components/ui/textarea";
import type { MissionProjection } from "../types";

export interface SteerFloPanelProps {
  readonly mission: MissionProjection;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
}

export function SteerFloPanel({ mission, open, onOpenChange }: SteerFloPanelProps) {
  return (
    <SidePanel
      open={open}
      onOpenChange={onOpenChange}
      title="Steer Flo"
      description={`Advisory guidance for mission ${mission.missionId}`}
      width="lg"
    >
      <div className="space-y-4">
        <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
          <p className="vf-text-body-s text-foreground font-medium">Steering is advisory.</p>
          <p className="vf-text-body-s text-muted-foreground mt-1">
            Flo may decline guidance that conflicts with policy or governance. Steering never
            changes governed economics directly: value changes still require a human-governed
            decision and deterministic recalculation.
          </p>
        </div>
        <div className="space-y-2">
          <label
            htmlFor="steer-flo-input"
            className="vf-text-body-s font-medium text-foreground"
          >
            Guidance for Flo
          </label>
          <Textarea
            id="steer-flo-input"
            disabled
            placeholder="Steering becomes available when the mission command channel is connected."
            aria-describedby="steer-flo-note"
            rows={4}
          />
          <p id="steer-flo-note" className="vf-text-caption text-muted-foreground">
            Unavailable in this slice: the mission command backend is not yet connected.
          </p>
        </div>
      </div>
    </SidePanel>
  );
}
