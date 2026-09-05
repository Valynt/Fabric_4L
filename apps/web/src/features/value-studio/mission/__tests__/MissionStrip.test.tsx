/**
 * Component tests for the mission status strip (§9.4, FE-MSN-*). Status is
 * icon + text (never color-only), progress exposes a progressbar role, and
 * Pause/Resume render ONLY when the backend allowedActions authorize them
 * (FE-MSN-006).
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import { makeMissionProjection } from "../fixtures";
import { VALUE_STUDIO_ACTIONS } from "../types";
import { MissionStrip, type MissionStripProps } from "../components/MissionStrip";

expect.extend(toHaveNoViolations);

function renderStrip(
  overrides: Parameters<typeof makeMissionProjection>[0] = {},
  stripProps: Partial<Pick<MissionStripProps, "commandPending" | "stale" | "offline">> = {},
) {
  const onPause = vi.fn();
  const onResume = vi.fn();
  const mission = makeMissionProjection(overrides);
  const utils = render(
    <MissionStrip
      mission={mission}
      onPause={onPause}
      onResume={onResume}
      commandPending={false}
      {...stripProps}
    />,
  );
  return { mission, onPause, onResume, ...utils };
}

describe("MissionStrip", () => {
  it("renders the mission title in a labelled region", () => {
    renderStrip();
    expect(
      screen.getByRole("region", { name: "Mission: Prepare Acme for CFO validation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Prepare Acme for CFO validation" })).toBeInTheDocument();
  });

  it("shows the status as text, never color-only (FE-A11Y-004)", () => {
    renderStrip({ status: "WAITING_FOR_HUMAN" });
    expect(screen.getByText("Waiting for you")).toBeInTheDocument();
  });

  it("shows coordination mode and autonomy summary", () => {
    renderStrip();
    expect(screen.getByText(/Delegated/)).toBeInTheDocument();
    expect(screen.getByText(/Supervised/)).toBeInTheDocument();
  });

  it("exposes an accessible progressbar for action progress", () => {
    renderStrip();
    const bar = screen.getByRole("progressbar", { name: "Mission action progress" });
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "9");
    expect(bar).toHaveAttribute("aria-valuenow", "6");
    expect(bar).toHaveAttribute("aria-valuetext", "6 of 9 actions completed");
  });

  it("renders the next action title, or explicit empty copy when none is queued", () => {
    const { unmount } = renderStrip();
    expect(screen.getByText("Rebuild CFO briefing from model VM-12")).toBeInTheDocument();
    unmount();
    renderStrip({ nextAction: null });
    expect(screen.getByText("No queued action")).toBeInTheDocument();
  });

  it("surfaces pending decisions with pluralized copy", () => {
    const { unmount } = renderStrip({ pendingDecisionCount: 2 });
    expect(screen.getByText("2 decisions are waiting for you.")).toBeInTheDocument();
    unmount();
    renderStrip({ pendingDecisionCount: 1 });
    expect(screen.getByText("1 decision is waiting for you.")).toBeInTheDocument();
  });

  it("hides the needs-decision block when nothing is pending", () => {
    renderStrip({ pendingDecisionCount: 0 });
    expect(screen.queryByText(/decision(s)? (is|are) waiting for you/)).not.toBeInTheDocument();
  });

  it("renders Pause only when the backend allows mission.pause (FE-MSN-006)", async () => {
    const user = userEvent.setup();
    const { onPause, unmount } = renderStrip();
    await user.click(screen.getByRole("button", { name: /Pause mission/ }));
    expect(onPause).toHaveBeenCalledTimes(1);
    unmount();

    renderStrip({ allowedActions: [VALUE_STUDIO_ACTIONS.steerFlo] });
    expect(screen.queryByRole("button", { name: /Pause mission/ })).not.toBeInTheDocument();
  });

  it("renders Resume only when the backend allows mission.resume", async () => {
    const user = userEvent.setup();
    const { onResume } = renderStrip({
      status: "PAUSED",
      allowedActions: [VALUE_STUDIO_ACTIONS.missionResume],
    });
    await user.click(screen.getByRole("button", { name: /Resume mission/ }));
    expect(onResume).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: /Pause mission/ })).not.toBeInTheDocument();
  });

  it("disables command buttons while a command is pending", () => {
    const mission = makeMissionProjection();
    render(
      <MissionStrip mission={mission} onPause={vi.fn()} onResume={vi.fn()} commandPending={true} />,
    );
    expect(screen.getByRole("button", { name: /Pause mission/ })).toBeDisabled();
  });

  it("disables ALL mission mutations while the projection is offline (PR #1679 R2)", () => {
    renderStrip(
      { allowedActions: [VALUE_STUDIO_ACTIONS.missionPause, VALUE_STUDIO_ACTIONS.missionResume] },
      { offline: true },
    );
    expect(screen.getByRole("button", { name: /Pause mission/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Resume mission/ })).toBeDisabled();
  });

  it("disables ALL mission mutations while the projection is stale (PR #1679 R2)", () => {
    renderStrip(
      { allowedActions: [VALUE_STUDIO_ACTIONS.missionPause, VALUE_STUDIO_ACTIONS.missionResume] },
      { stale: true },
    );
    expect(screen.getByRole("button", { name: /Pause mission/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Resume mission/ })).toBeDisabled();
  });

  it("keeps mission mutations enabled in the ready state", () => {
    renderStrip(
      { allowedActions: [VALUE_STUDIO_ACTIONS.missionPause] },
      { stale: false, offline: false },
    );
    expect(screen.getByRole("button", { name: /Pause mission/ })).toBeEnabled();
  });

  it("has no axe violations", async () => {
    const { container } = renderStrip();
    expect(await axe(container)).toHaveNoViolations();
  });
});
