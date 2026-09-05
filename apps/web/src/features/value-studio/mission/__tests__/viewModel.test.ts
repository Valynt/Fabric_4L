/**
 * Unit tests for projection → view-model mapping (FE-IMP-002/003/004,
 * FE-A11Y-004, FE-ACT-007). Mapping never fabricates values: missing data maps
 * to explicit contract copy, never zero.
 */

import { describe, expect, it } from "vitest";

import { AUDIENCE_LENSES } from "../types";
import {
  AUTONOMY_DISPLAY,
  COORDINATION_MODE_DISPLAY,
  formatGovernanceLabel,
  formatMoneyAnnual,
  formatMoneyFull,
  formatProgramCost,
  formatRoi,
  GOVERNANCE_LABEL_DISPLAY,
  JOURNEY_STAGE_DISPLAY,
  LENS_DISPLAY,
  MISSION_STATUS_DISPLAY,
  orderActivityEvents,
  PUBLICATION_STATE_DISPLAY,
} from "../viewModel";

describe("money and ratio formatting (§1.4 display style)", () => {
  it("formats full money with grouped digits and currency code", () => {
    expect(formatMoneyFull({ amount: 720_000, currency: "USD" })).toBe("720,000 USD");
    expect(formatMoneyFull({ amount: 1_440_000, currency: "USD" })).toBe("1,440,000 USD");
  });

  it("formats annual benefit with the /year suffix", () => {
    expect(formatMoneyAnnual({ amount: 720_000, currency: "USD" })).toBe("720,000 USD/year");
  });

  it("renders a null program cost as Pending, never zero (FE-IMP-002)", () => {
    expect(formatProgramCost(null)).toBe("Pending");
    expect(
      formatProgramCost({ amount: 96_000, currency: "USD", governanceLabel: "PROVISIONAL" }),
    ).toBe("96,000 USD/year");
  });

  it("renders a null ROI as Not yet calculable, never zero (FE-IMP-003)", () => {
    expect(formatRoi(null)).toBe("Not yet calculable");
    expect(formatRoi({ ratio: 7.5, governanceLabel: "PROVISIONAL" })).toBe("7.50×");
  });
});

describe("enum display maps", () => {
  it("maps backend governance labels to display text (FE-HDR-003)", () => {
    expect(formatGovernanceLabel("PROVISIONAL")).toBe("Provisional");
    expect(GOVERNANCE_LABEL_DISPLAY).toEqual({
      PROVISIONAL: "Provisional",
      VALIDATED: "Validated",
      APPROVED: "Approved",
    });
  });

  it("provides display text for every audience lens (FE-LENS-001)", () => {
    for (const lens of AUDIENCE_LENSES) {
      expect(LENS_DISPLAY[lens]).toBeTruthy();
    }
    expect(LENS_DISPLAY.cfo).toBe("CFO");
    expect(LENS_DISPLAY.canonical).toBe("Canonical");
  });

  it("maps mission statuses to human copy (text always accompanies color)", () => {
    expect(MISSION_STATUS_DISPLAY.WAITING_FOR_HUMAN).toBe("Waiting for you");
    expect(MISSION_STATUS_DISPLAY.EXECUTING).toBe("Executing");
    expect(MISSION_STATUS_DISPLAY.FAILED).toBe("Failed");
  });

  it("maps coordination, autonomy, journey, and publication enums exhaustively", () => {
    expect(COORDINATION_MODE_DISPLAY.DELEGATED).toBe("Delegated");
    expect(AUTONOMY_DISPLAY.SUPERVISED).toBe("Supervised");
    expect(JOURNEY_STAGE_DISPLAY.review).toBe("Review");
    expect(PUBLICATION_STATE_DISPLAY.BLOCKED).toBe("Publication Blocked");
  });
});

describe("orderActivityEvents (FE-ACT-007)", () => {
  const makeEvent = (sequence: number, eventId: string) => ({ sequence, eventId });

  it("sorts by ascending sequence", () => {
    const ordered = orderActivityEvents([makeEvent(103, "c"), makeEvent(101, "a"), makeEvent(102, "b")]);
    expect(ordered.map((e) => e.eventId)).toEqual(["a", "b", "c"]);
  });

  it("dedupes by eventId keeping the first occurrence in sequence order", () => {
    const ordered = orderActivityEvents([
      makeEvent(102, "dup"),
      makeEvent(101, "dup"),
      makeEvent(103, "c"),
    ]);
    expect(ordered.map((e) => e.eventId)).toEqual(["dup", "c"]);
    expect(ordered[0]?.sequence).toBe(101);
  });

  it("does not mutate the input array", () => {
    const input = [makeEvent(2, "b"), makeEvent(1, "a")];
    const snapshot = [...input];
    orderActivityEvents(input);
    expect(input).toEqual(snapshot);
  });
});
