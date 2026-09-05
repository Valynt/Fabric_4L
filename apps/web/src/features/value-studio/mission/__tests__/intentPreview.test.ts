/**
 * Contract tests for the typed intent-preview builder (FE-INTENT-001, §9.9).
 * Every interpolated value must come from the decision projection or the typed
 * draft — never from free-form model text.
 */

import { describe, expect, it } from "vitest";

import { makeDecisionProjection } from "../fixtures";
import {
  buildAcceptRecommendationPreview,
  buildDeferDecisionPreview,
  buildEditDecisionPreview,
} from "../intentPreview";

const decision = makeDecisionProjection();

describe("buildAcceptRecommendationPreview", () => {
  it("builds the DISP-01 accept preview from projection values only", () => {
    const preview = buildAcceptRecommendationPreview(decision);

    expect(preview.commandType).toBe("working_target.accept");
    expect(preview.expectedModelVersion).toBe("VM-12");
    expect(preview.expectedDecisionVersion).toBe(3);
    expect(preview.decisionId).toBe(decision.decisionId);
    expect(preview.payload).toEqual({
      kind: "accept",
      workingValue: 340,
      workingUnit: "hours/year",
      alternativeValue: 280,
      alternativeUnit: "hours/year",
    });
    expect(preview.will).toEqual([
      "set the working downtime target to 340 hours/year;",
      "retain 280 hours/year as an upside scenario;",
      "request deterministic recalculation;",
      "resume MISSION-204 from its waiting checkpoint.",
    ]);
    expect(preview.willNot).toEqual([
      "approve a program cost;",
      "calculate ROI if cost is unavailable;",
      "publish a deliverable;",
      "clear unrelated blockers.",
    ]);
  });
});

describe("buildEditDecisionPreview", () => {
  it("interpolates the draft values and falls back to the projected scope", () => {
    const preview = buildEditDecisionPreview(decision, {
      workingHours: 320,
      alternativeHours: 280,
      rationale: "CFO asked for a conservative target.",
    });

    expect(preview.commandType).toBe("decision.edit");
    expect(preview.expectedModelVersion).toBe("VM-12");
    expect(preview.expectedDecisionVersion).toBe(3);
    expect(preview.will).toEqual([
      "set the working downtime target to 320 hours/year;",
      "set the alternative to 280 hours/year (Upside scenario only);",
      "record the supplied rationale on the decision;",
      "request deterministic recalculation;",
    ]);
    expect(preview.willNot).toContain("clear unrelated blockers.");
  });

  it("omits the alternative line when no alternative is drafted", () => {
    const preview = buildEditDecisionPreview(decision, {
      workingHours: 340,
      rationale: "",
    });

    expect(preview.will).toEqual([
      "set the working downtime target to 340 hours/year;",
      "record the supplied rationale on the decision;",
      "request deterministic recalculation;",
    ]);
  });

  it("prefers the drafted scope note over the projected one", () => {
    const preview = buildEditDecisionPreview(decision, {
      workingHours: 340,
      alternativeHours: 300,
      alternativeScope: "Stretch case reviewed with finance",
      rationale: "Aligns with the finance workbook.",
    });

    expect(preview.will[1]).toBe(
      "set the alternative to 300 hours/year (Stretch case reviewed with finance);",
    );
  });
});

describe("buildDeferDecisionPreview", () => {
  it("builds the defer preview and extends the will-not list", () => {
    const preview = buildDeferDecisionPreview(decision, {
      ownerDisplayName: "R. Chen",
      dueAt: "2026-09-01",
      reason: "Waiting on the finance workbook.",
    });

    expect(preview.commandType).toBe("decision.defer");
    expect(preview.expectedModelVersion).toBe("VM-12");
    expect(preview.expectedDecisionVersion).toBe(3);
    expect(preview.will).toEqual([
      "defer DISP-01 to R. Chen until 2026-09-01;",
      "pause dependent artifact regeneration until the due date;",
      "record the defer reason: Waiting on the finance workbook.;",
    ]);
    expect(preview.willNot).toEqual([
      "change the working downtime target;",
      "approve a program cost;",
      "calculate ROI if cost is unavailable;",
      "publish a deliverable;",
      "clear unrelated blockers.",
    ]);
  });
});
