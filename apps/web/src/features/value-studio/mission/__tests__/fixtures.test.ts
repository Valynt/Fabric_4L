/**
 * Contract tests for the deterministic fixture factory (STEP 2, §1.4).
 * Fixtures stand in for the authoritative backend projection during Phase 1:
 * hand-authored, deterministic, fixed ISO timestamps — no browser clocks, no
 * randomness. The ten named states are the Slice-1 state matrix.
 */

import { describe, expect, it } from "vitest";

import {
  DEFAULT_VALUE_STUDIO_FIXTURE,
  FIXTURE_NOW,
  getValueStudioFixture,
  isValueStudioFixtureName,
  makeValueStudioProjection,
  VALUE_STUDIO_FIXTURE_NAMES,
  VALUE_STUDIO_REFERENCE_IDS,
} from "../fixtures";
import { VALUE_STUDIO_ACTIONS } from "../types";

describe("named state registry", () => {
  it("declares exactly the ten contract states in order", () => {
    expect(VALUE_STUDIO_FIXTURE_NAMES).toEqual([
      "loading",
      "blocked",
      "empty",
      "partial",
      "error",
      "offline",
      "stale",
      "unauthorized",
      "resolved-decision-but-still-finance-blocked",
      "static-renderer-fallback",
    ]);
  });

  it("uses blocked — the §1.4 reference state — as the default", () => {
    expect(DEFAULT_VALUE_STUDIO_FIXTURE).toBe("blocked");
  });

  it("guards fixture names totally", () => {
    for (const name of VALUE_STUDIO_FIXTURE_NAMES) {
      expect(isValueStudioFixtureName(name)).toBe(true);
    }
    expect(isValueStudioFixtureName("not-a-state")).toBe(false);
    expect(isValueStudioFixtureName("")).toBe(false);
    expect(isValueStudioFixtureName(null)).toBe(false);
  });

  it("returns a result echoing the requested name for every state", () => {
    for (const name of VALUE_STUDIO_FIXTURE_NAMES) {
      expect(getValueStudioFixture(name).name).toBe(name);
    }
  });
});

describe("deterministic reference constants", () => {
  it("pins the fixture clock to a fixed instant", () => {
    expect(FIXTURE_NOW).toBe("2026-08-24T14:30:00.000Z");
  });

  it("pins the §1.4 reference identifiers", () => {
    expect(VALUE_STUDIO_REFERENCE_IDS).toEqual({
      tenantId: "tenant_valynt_demo",
      accountId: "acct_acme_manufacturing",
      opportunityId: "OPP-1842",
      caseId: "case_acme_opp1842",
      missionId: "MISSION-204",
      decisionId: "DISP-01",
      patchArtifactId: "artifact_patch_vm12",
      modelVersion: "VM-12",
    });
  });

  it("is deterministic across calls (deep-equal projections)", () => {
    expect(getValueStudioFixture("blocked")).toEqual(getValueStudioFixture("blocked"));
    expect(makeValueStudioProjection()).toEqual(makeValueStudioProjection());
  });
});

describe("blocked — the §1.4 reference economic state", () => {
  const view = getValueStudioFixture("blocked").view;

  it("is a ready view", () => {
    expect(view.kind).toBe("ready");
  });

  it("carries the reference economics: 720k provisional benefit, no cost, no ROI", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    const { economics } = view.projection.case;
    expect(economics.annualBenefit).toEqual({
      amount: 720_000,
      currency: "USD",
      governanceLabel: "PROVISIONAL",
    });
    expect(economics.programCost).toBeNull();
    expect(economics.roi).toBeNull();
    expect(economics.formulaDisplay).toBe("(400 − 340) × 12,000 USD = 720,000 USD/year");
  });

  it("is governance-blocked behind DISP-01 with DISP-02 also unresolved", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    expect(view.projection.case.governance).toEqual({
      primaryBlockerId: "DISP-01",
      publicationState: "BLOCKED",
      unresolvedDecisionIds: ["DISP-01", "DISP-02"],
      validationState: "Pending finance validation",
      approvalState: "Not approved",
    });
  });

  it("exposes only backend-allowed actions on the case", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    expect(view.projection.case.allowedActions).toEqual([
      VALUE_STUDIO_ACTIONS.decisionSubmit,
      VALUE_STUDIO_ACTIONS.decisionEdit,
      VALUE_STUDIO_ACTIONS.decisionDefer,
      VALUE_STUDIO_ACTIONS.evidenceView,
    ]);
  });

  it("carries the open DISP-01 decision with the 340/280 conflict", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    const { decision } = view.projection;
    expect(decision?.decisionId).toBe("DISP-01");
    expect(decision?.status).toBe("OPEN");
    expect(decision?.decisionVersion).toBe(3);
    expect(decision?.currentWorkingValue).toEqual({ value: 340, unit: "hours/year" });
    expect(decision?.alternative).toEqual({
      value: 280,
      unit: "hours/year",
      proposedScope: "Upside scenario only",
    });
    expect(decision?.calculatedImpact.workingAnnualBenefit).toEqual({
      amount: 720_000,
      currency: "USD",
    });
    expect(decision?.calculatedImpact.alternativeAnnualBenefit).toEqual({
      amount: 1_440_000,
      currency: "USD",
    });
  });

  it("carries the mission at version 7, executing, two pending decisions", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    const { mission } = view.projection;
    expect(mission?.version).toBe(7);
    expect(mission?.status).toBe("EXECUTING");
    expect(mission?.pendingDecisionCount).toBe(2);
    expect(mission?.allowedActions).toEqual([
      VALUE_STUDIO_ACTIONS.missionPause,
      VALUE_STUDIO_ACTIONS.steerFlo,
    ]);
  });

  it("carries the five-item model patch in contract order", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    expect(view.projection.patch?.items.map((i) => i.status)).toEqual([
      "proposed",
      "proposed",
      "pending",
      "completed",
      "blocked",
    ]);
  });

  it("carries nine activity events with strictly increasing sequences", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    const events = view.projection.activity;
    expect(events).toHaveLength(9);
    const sequences = events.map((e) => e.sequence);
    const sorted = [...sequences].sort((a, b) => a - b);
    expect(sequences).toEqual(sorted);
    expect(events[0]?.eventId).toBe("evt_101");
    expect(events[8]?.eventId).toBe("evt_109");
  });

  it("links three evidence references, EV-1003 restricted with no excerpt", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    const evidence = view.projection.decision?.evidence ?? [];
    expect(evidence.map((e) => e.evidenceId)).toEqual(["EV-1001", "EV-1002", "EV-1003"]);
    const restricted = evidence.find((e) => e.evidenceId === "EV-1003");
    expect(restricted?.restricted).toBe(true);
    expect("excerpt" in restricted).toBe(false);
  });
});

describe("loading state", () => {
  it("is a bare loading view", () => {
    expect(getValueStudioFixture("loading").view).toEqual({ kind: "loading" });
  });
});

describe("empty state", () => {
  it("has no mission, patch, decision, or activity; branch comparison awaits calculation", () => {
    const view = getValueStudioFixture("empty").view;
    expect(view.kind).toBe("empty");
    if (view.kind !== "empty") throw new Error("expected empty view");
    expect(view.reason).toContain("No active mission");
    expect(view.projection.mission).toBeNull();
    expect(view.projection.patch).toBeNull();
    expect(view.projection.decision).toBeNull();
    expect(view.projection.activity).toEqual([]);
    expect(view.projection.branchComparison?.status).toBe("AWAITING_AUTHORITATIVE_CALCULATION");
    expect(view.projection.branchComparison?.branches).toEqual([]);
  });
});

describe("partial state (§11.4)", () => {
  it("loads case and decision while the activity section is unavailable", () => {
    const view = getValueStudioFixture("partial").view;
    expect(view.kind).toBe("partial");
    if (view.kind !== "partial") throw new Error("expected partial view");
    expect(view.projection.partial?.unavailableSections).toEqual(["activity"]);
    expect(view.projection.partial?.reasons.activity).toContain("corr_fixture_partial_01");
    expect(view.projection.decision?.decisionId).toBe("DISP-01");
  });
});

describe("error state", () => {
  it("is retryable with a correlation id", () => {
    const view = getValueStudioFixture("error").view;
    expect(view).toEqual({
      kind: "error",
      message: "The value case could not be loaded.",
      correlationId: "corr_fixture_error_01",
      retryable: true,
    });
  });
});

describe("offline state", () => {
  it("keeps the last known projection with a fixed sync timestamp", () => {
    const view = getValueStudioFixture("offline").view;
    expect(view.kind).toBe("offline");
    if (view.kind !== "offline") throw new Error("expected offline view");
    expect(view.lastSyncedAt).toBe(FIXTURE_NOW);
    expect(view.projection.case.caseId).toBe("case_acme_opp1842");
  });
});

describe("stale state", () => {
  it("reports the model/decision version skew", () => {
    const view = getValueStudioFixture("stale").view;
    expect(view.kind).toBe("stale");
    if (view.kind !== "stale") throw new Error("expected stale view");
    expect(view.projection.stale).toMatchObject({
      expectedModelVersion: "VM-12",
      currentModelVersion: "VM-13",
      expectedDecisionVersion: 3,
      currentDecisionVersion: 4,
    });
  });
});

describe("unauthorized state (§8.1)", () => {
  it("carries no protected body data", () => {
    const view = getValueStudioFixture("unauthorized").view;
    expect(view.kind).toBe("unauthorized");
    if (view.kind !== "unauthorized") throw new Error("expected unauthorized view");
    expect(view.reason).toBe("forbidden");
    expect("projection" in view).toBe(false);
  });
});

describe("resolved-decision-but-still-finance-blocked (FE-DEC-006)", () => {
  const view = getValueStudioFixture("resolved-decision-but-still-finance-blocked").view;

  it("resolves DISP-01 while publication stays blocked behind FIN-02", () => {
    expect(view.kind).toBe("ready");
    if (view.kind !== "ready") throw new Error("expected ready view");
    expect(view.projection.decision?.status).toBe("RESOLVED");
    expect(view.projection.decision?.resolution?.outcomeLabel).toBe("Working target accepted");
    expect(view.projection.case.governance.primaryBlockerId).toBe("FIN-02");
    expect(view.projection.case.governance.publicationState).toBe("BLOCKED");
  });

  it("narrows decision actions to evidence viewing only", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    expect(view.projection.decision?.allowedActions).toEqual([
      VALUE_STUDIO_ACTIONS.evidenceView,
    ]);
  });

  it("appends the human resolution event to the activity trail", () => {
    if (view.kind !== "ready") throw new Error("expected ready view");
    const last = view.projection.activity[view.projection.activity.length - 1];
    expect(last?.eventId).toBe("evt_110");
    expect(last?.eventType).toBe("decision.resolved");
    expect(last?.actorType).toBe("HUMAN");
    expect(last?.actorDisplayName).toBe("R. Chen");
  });
});

describe("static-renderer-fallback state", () => {
  it("selects the CFO lens with a recorded generative-UI render failure", () => {
    const view = getValueStudioFixture("static-renderer-fallback").view;
    expect(view.kind).toBe("ready");
    if (view.kind !== "ready") throw new Error("expected ready view");
    expect(view.projection.activeLens).toBe("cfo");
    expect(view.projection.generativeUiFallback).toEqual({
      componentName: "LensRenderer:cfo",
      failureClass: "RENDER_ERROR",
    });
  });
});
