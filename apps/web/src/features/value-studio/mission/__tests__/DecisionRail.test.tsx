/**
 * Component tests for the Review Required decision rail (§9.9, FE-RAIL-001…009).
 * Action buttons render ONLY for backend-authorized allowedActions; submissions
 * pause while stale/offline; resolution state comes from the payload, never
 * from UI inference (FE-DEC-004/005).
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { getValueStudioFixture, makeDecisionProjection } from "../fixtures";
import { VALUE_STUDIO_ACTIONS } from "../types";
import { DecisionRail } from "../components/DecisionRail";

function renderRail(overrides: Partial<Parameters<typeof DecisionRail>[0]> = {}) {
  const props = {
    decision: makeDecisionProjection(),
    stale: false,
    submitting: false,
    onAccept: vi.fn(),
    onEdit: vi.fn(),
    onDefer: vi.fn(),
    onOpenEvidence: vi.fn(),
    onClose: vi.fn(),
    ...overrides,
  };
  const utils = render(<DecisionRail {...props} />);
  return { ...props, ...utils };
}

describe("DecisionRail — projection rendering", () => {
  it("renders the rail with heading, version line, and escalation reason", () => {
    renderRail();
    expect(
      screen.getByRole("complementary", { name: "Review required: Resolve downtime target conflict" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Review required — DISP-01" })).toBeInTheDocument();
    expect(screen.getByText(/Decision version 3 · model VM-12 · status OPEN/)).toBeInTheDocument();
    expect(
      screen.getByText(/Working target \(340 hours\/year\) conflicts with the upside scenario/),
    ).toBeInTheDocument();
  });

  it("renders working and alternative values and read-only calculated impact", () => {
    renderRail();
    expect(screen.getByText("340 hours/year")).toBeInTheDocument();
    expect(screen.getByText("280 hours/year")).toBeInTheDocument();
    expect(screen.getByText("Upside scenario only")).toBeInTheDocument();
    expect(screen.getByText("720,000 USD/year")).toBeInTheDocument();
    expect(screen.getByText("1,440,000 USD/year")).toBeInTheDocument();
    // Read-only: no numeric inputs in the impact grid.
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  });

  it("renders sensitivity, recommendation, and governance rows verbatim", () => {
    renderRail();
    expect(
      screen.getByText("±20 hours moves annual benefit by ±240,000 USD"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Accept the working target of 340 hours/year and retain 280 hours/year as an upside scenario.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Full lineage to telemetry export EVT-4419")).toBeInTheDocument();
    expect(screen.getAllByText("Pending finance validation").length).toBeGreaterThan(0);
    expect(screen.getByText("Value Engineer or above")).toBeInTheDocument();
  });

  it("renders the Why Flo stopped detail from the escalation payload", () => {
    renderRail();
    expect(screen.getByText("Why Flo stopped")).toBeInTheDocument();
    expect(
      screen.getByText("Working target and upside scenario disagree on the downtime target."),
    ).toBeInTheDocument();
    expect(screen.getByText(/svc-calc-88/)).toBeInTheDocument();
    expect(screen.getByText(/Flo lacks authority to resolve it/)).toBeInTheDocument();
    expect(
      screen.getByText("Human review of DISP-01 with evidence pack EV-1001 through EV-1003."),
    ).toBeInTheDocument();
  });

  it("moves focus to the rail heading on mount (deep-link focus, FE-A11Y-009)", () => {
    renderRail();
    expect(screen.getByRole("heading", { name: "Review required — DISP-01" })).toHaveFocus();
  });
});

describe("DecisionRail — evidence access", () => {
  it("opens evidence entries through the callback and marks restricted items", async () => {
    const user = userEvent.setup();
    const { onOpenEvidence, decision } = renderRail();
    await user.click(
      screen.getByRole("button", {
        name: "Open evidence EV-1001: Downtime telemetry export FY-2026",
      }),
    );
    expect(onOpenEvidence).toHaveBeenCalledWith(
      expect.objectContaining({ evidenceId: "EV-1001" }),
    );
    expect(decision.evidence).toHaveLength(3);
    expect(screen.getByText("Restricted")).toBeInTheDocument();
  });

  it("disables evidence buttons and explains when evidence.view is not granted", () => {
    renderRail({
      decision: makeDecisionProjection({
        allowedActions: [
          VALUE_STUDIO_ACTIONS.decisionSubmit,
          VALUE_STUDIO_ACTIONS.decisionEdit,
          VALUE_STUDIO_ACTIONS.decisionDefer,
        ],
      }),
    });
    expect(
      screen.getByRole("button", { name: /Open evidence EV-1001/ }),
    ).toBeDisabled();
    expect(
      screen.getByText("Evidence access is not granted for your role on this decision."),
    ).toBeInTheDocument();
  });
});

describe("DecisionRail — action gating", () => {
  it("invokes accept and edit callbacks from backend-authorized buttons", async () => {
    const user = userEvent.setup();
    const { onAccept, onEdit } = renderRail();
    await user.click(screen.getByRole("button", { name: "Accept recommendation" }));
    expect(onAccept).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Edit decision" }));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("renders no mutation buttons when the backend does not authorize them", () => {
    renderRail({
      decision: makeDecisionProjection({
        allowedActions: [VALUE_STUDIO_ACTIONS.evidenceView],
      }),
    });
    expect(screen.queryByRole("button", { name: "Accept recommendation" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit decision" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Defer decision" })).not.toBeInTheDocument();
  });

  it("pauses submissions while stale, with an alert (FE-RAIL-008)", () => {
    renderRail({ stale: true });
    expect(screen.getByRole("alert")).toHaveTextContent("This decision changed on the server.");
    expect(screen.getByRole("button", { name: "Accept recommendation" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Edit decision" })).toBeDisabled();
  });

  it("pauses submissions while offline, with a status notice (FE-RAIL-009)", () => {
    renderRail({ offline: true });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Offline: decision actions are paused until the connection returns.",
    );
    expect(screen.getByRole("button", { name: "Accept recommendation" })).toBeDisabled();
  });

  it("shows the submitting state on the accept button", () => {
    renderRail({ submitting: true });
    const accept = screen.getByRole("button", { name: "Submitting…" });
    expect(accept).toBeDisabled();
  });
});

describe("DecisionRail — defer flow", () => {
  it("requires owner, due date, and reason before continuing", async () => {
    const user = userEvent.setup();
    const { onDefer } = renderRail();

    await user.click(screen.getByRole("button", { name: "Defer decision" }));
    const continueButton = screen.getByRole("button", { name: "Continue to preview" });
    expect(continueButton).toBeDisabled();

    await user.type(screen.getByLabelText("Defer to"), "R. Chen");
    await user.type(screen.getByLabelText("Due date"), "2026-09-01");
    await user.type(screen.getByLabelText("Reason"), "Waiting on the finance workbook.");
    expect(continueButton).toBeEnabled();

    await user.click(continueButton);
    expect(onDefer).toHaveBeenCalledWith({
      ownerDisplayName: "R. Chen",
      dueAt: "2026-09-01",
      reason: "Waiting on the finance workbook.",
    });
  });
});

describe("DecisionRail — resolved decision (FE-DEC-004/005/006)", () => {
  const resolvedView = getValueStudioFixture("resolved-decision-but-still-finance-blocked").view;
  if (resolvedView.kind !== "ready" || !resolvedView.projection.decision) {
    throw new Error("resolved fixture must carry a decision");
  }
  const resolvedDecision = resolvedView.projection.decision;

  it("shows the resolution from the payload and no mutation controls", () => {
    renderRail({ decision: resolvedDecision });
    expect(screen.getByText("Working target accepted")).toBeInTheDocument();
    expect(screen.getByText(/Resolved by R\. Chen/)).toBeInTheDocument();
    expect(
      screen.getByText(/Finance validation and program-cost approval remain open\./),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept recommendation" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit decision" })).not.toBeInTheDocument();
  });

  it("never invents a Locked label (FE-DEC-005)", () => {
    renderRail({ decision: resolvedDecision });
    expect(screen.queryByText(/locked/i)).not.toBeInTheDocument();
  });

  it("closes via the close button", async () => {
    const user = userEvent.setup();
    const { onClose } = renderRail();
    await user.click(screen.getByRole("button", { name: "Close decision rail" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
