/**
 * Value Studio (mission-led) — mission activity feed (contract §9.12, FE-ACT-*).
 *
 * Chronological, tamper-evident event list: deterministic ordering with
 * dedupe by eventId (FE-ACT-007), expandable rows (aria-expanded/controls)
 * revealing correlation ID and affected objects, and an Undo control ONLY
 * when the event's backend allowedActions authorizes `activity.undo`
 * (FE-ACT-005). Status is icon + text, never color-only. The feed announces
 * updates via aria-live="polite".
 */

import { useState } from "react";
import { ChevronDown, Undo2 } from "lucide-react";
import { Btn } from "@/components/ui/fabric/Btn";
import { FabricCard } from "@/components/ui/fabric/FabricCard";
import { formatDate } from "@/lib/formatters";
import { cn } from "@/lib/utils";
import type { MissionActivityEvent, MissionActivityStatus } from "../types";
import { orderActivityEvents } from "../viewModel";

export interface MissionActivityFeedProps {
  readonly events: readonly MissionActivityEvent[];
  readonly onUndo: (eventId: string) => void;
  readonly onEventExpanded: (eventId: string) => void;
}

const STATUS_LABEL: Record<MissionActivityStatus, string> = {
  STARTED: "Started",
  COMPLETED: "Completed",
  WAITING: "Waiting",
  FAILED: "Failed",
  RETRIED: "Retried",
};

const STATUS_CLASSES: Record<MissionActivityStatus, string> = {
  STARTED: "bg-primary/10 text-primary",
  COMPLETED: "bg-success/10 text-success",
  WAITING: "bg-warning/10 text-warning",
  FAILED: "bg-destructive/10 text-destructive",
  RETRIED: "bg-warning/10 text-warning",
};

const ACTOR_LABEL: Record<MissionActivityEvent["actorType"], string> = {
  HUMAN: "You",
  AGENT: "Flo",
  SYSTEM: "System",
};

export function MissionActivityFeed({
  events,
  onUndo,
  onEventExpanded,
}: MissionActivityFeedProps) {
  const [expandedIds, setExpandedIds] = useState<ReadonlySet<string>>(new Set());
  const ordered = orderActivityEvents(events);

  const toggle = (eventId: string) => {
    setExpandedIds((previous) => {
      const next = new Set(previous);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
        onEventExpanded(eventId);
      }
      return next;
    });
  };

  return (
    <FabricCard title="Mission activity" padding="normal">
      <ol className="space-y-1" aria-label="Mission activity events" aria-live="polite">
        {ordered.map((event) => {
          const expanded = expandedIds.has(event.eventId);
          const detailId = `activity-detail-${event.eventId}`;
          const canUndo = event.allowedActions.includes("activity.undo");
          return (
            <li key={event.eventId} className="rounded-md border border-transparent">
              <button
                type="button"
                aria-expanded={expanded}
                aria-controls={detailId}
                onClick={() => toggle(event.eventId)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-md px-2 py-2 text-left",
                  "hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                )}
              >
                <ChevronDown
                  className={cn(
                    "h-4 w-4 mt-0.5 shrink-0 text-muted-foreground transition-transform",
                    expanded && "rotate-180",
                  )}
                  aria-hidden="true"
                />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="vf-text-body-s font-medium text-foreground">
                      {event.summary}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        STATUS_CLASSES[event.status],
                      )}
                    >
                      {STATUS_LABEL[event.status]}
                    </span>
                  </span>
                  <span className="vf-text-caption text-muted-foreground">
                    {ACTOR_LABEL[event.actorType]} ·{" "}
                    <time dateTime={event.occurredAt}>{formatDate(event.occurredAt)}</time>
                  </span>
                </span>
              </button>
              {expanded && (
                <div id={detailId} className="ml-9 space-y-2 px-2 pb-3">
                  <dl className="space-y-1 vf-text-caption text-muted-foreground">
                    <div className="flex gap-2">
                      <dt className="font-medium">Event</dt>
                      <dd>
                        {event.eventType} · seq {event.sequence}
                        {event.modelVersion ? ` · model ${event.modelVersion}` : ""}
                      </dd>
                    </div>
                    <div className="flex gap-2">
                      <dt className="font-medium">Correlation</dt>
                      <dd className="font-mono">{event.correlationId}</dd>
                    </div>
                    {event.objectIds.length > 0 && (
                      <div className="flex gap-2">
                        <dt className="font-medium">Objects</dt>
                        <dd>{event.objectIds.join(", ")}</dd>
                      </div>
                    )}
                  </dl>
                  {canUndo && (
                    <Btn
                      variant="ghost"
                      size="sm"
                      onClick={() => onUndo(event.eventId)}
                      aria-label={`Undo event ${event.eventId}`}
                    >
                      <Undo2 className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                      Undo this step
                    </Btn>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </FabricCard>
  );
}
