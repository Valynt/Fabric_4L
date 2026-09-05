/**
 * Component tests for the mission activity feed gating contract (PR #1679
 * review, R2): the Undo control is a mission mutation, so it follows the same
 * stale/offline gating as decision submissions (FE-RAIL-008/009) and the
 * MissionStrip pause/resume controls.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { MissionActivityEvent } from "../types";
import { MissionActivityFeed } from "../components/MissionActivityFeed";

function makeUndoableEvent(): MissionActivityEvent {
  return {
    eventId: "evt_undo_1",
    missionId: "mission_204",
    caseId: "case_acme_opp1842",
    sequence: 105,
    occurredAt: "2026-08-24T10:00:00.000Z",
    actorType: "AGENT",
    actorDisplayName: "Flo",
    eventType: "calculation.completed",
    status: "COMPLETED",
    summary: "Recomputed annual benefit.",
    objectIds: ["metric_annual_benefit"],
    correlationId: "corr_mission_204_05",
    reversible: true,
    allowedActions: ["activity.undo"],
  } as MissionActivityEvent;
}

function renderFeed(degraded: { stale?: boolean; offline?: boolean } = {}) {
  const onUndo = vi.fn();
  const utils = render(
    <MissionActivityFeed
      events={[makeUndoableEvent()]}
      onUndo={onUndo}
      onEventExpanded={vi.fn()}
      {...degraded}
    />,
  );
  return { onUndo, ...utils };
}

async function expandFirstEvent() {
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /Recomputed annual benefit/ }));
  return user;
}

describe("MissionActivityFeed degraded-state gating", () => {
  it("enables Undo for an authorized event in the ready state", async () => {
    const { onUndo } = renderFeed();
    const user = await expandFirstEvent();
    const undo = await screen.findByRole("button", { name: "Undo event evt_undo_1" });
    expect(undo).toBeEnabled();
    await user.click(undo);
    expect(onUndo).toHaveBeenCalledWith("evt_undo_1");
  });

  it("disables Undo while the projection is stale", async () => {
    renderFeed({ stale: true });
    await expandFirstEvent();
    expect(await screen.findByRole("button", { name: "Undo event evt_undo_1" })).toBeDisabled();
  });

  it("disables Undo while the projection is offline", async () => {
    renderFeed({ offline: true });
    await expandFirstEvent();
    expect(await screen.findByRole("button", { name: "Undo event evt_undo_1" })).toBeDisabled();
  });
});
