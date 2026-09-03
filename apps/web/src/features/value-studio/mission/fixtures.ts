/**
 * Value Studio (mission-led) — deterministic fixture factory.
 *
 * Contract: FE-VOS-STUDIO-001, STEP 2 (typed fixtures) and §1.4 (reference
 * economic state). Fixtures stand in for the authoritative backend projection
 * during Phase 1. They are hand-authored, deterministic, and use fixed ISO
 * timestamps — no browser clocks, no randomness, no model-generated content.
 *
 * The front end never derives or overwrites these values; components receive
 * them read-only through the adapter seam (`adapter.ts`).
 */

import type {
  BranchComparisonProjection,
  DecisionRequestProjection,
  EvidenceReference,
  IsoDateTime,
  JourneyProjection,
  MissionActivityEvent,
  MissionProjection,
  ModelPatchProjection,
  ValueStudioCaseProjection,
  ValueStudioProjection,
  ValueStudioViewState,
} from "./types";
import { VALUE_STUDIO_ACTIONS } from "./types";

// ── Fixed clock ──────────────────────────────────────────────────────────────

/**
 * Single fixed reference instant for every fixture. Using one exported
 * constant keeps fixture timelines internally consistent and reviewable.
 */
export const FIXTURE_NOW: IsoDateTime = "2026-08-24T14:30:00.000Z";

/** Fixed capture times used by evidence fixtures (literal, reviewable). */
const EVIDENCE_CAPTURED = {
  telemetry: "2026-08-12T14:30:00.000Z",
  timeStudy: "2026-08-19T14:30:00.000Z",
  financeWorkbook: "2026-08-04T14:30:00.000Z",
} as const;

// ── Reference identifiers (contract §1.4 / Slice-1 reference case) ───────────

export const VALUE_STUDIO_REFERENCE_IDS = {
  tenantId: "tenant_valynt_demo",
  accountId: "acct_acme_manufacturing",
  opportunityId: "OPP-1842",
  caseId: "case_acme_opp1842",
  missionId: "MISSION-204",
  decisionId: "DISP-01",
  patchArtifactId: "artifact_patch_vm12",
  modelVersion: "VM-12",
} as const;

// ── Case projection (contract §7.1, reference values §1.4) ───────────────────

export function makeCaseProjection(
  overrides: Partial<ValueStudioCaseProjection> = {},
): ValueStudioCaseProjection {
  return {
    tenantId: VALUE_STUDIO_REFERENCE_IDS.tenantId,
    accountId: VALUE_STUDIO_REFERENCE_IDS.accountId,
    opportunityId: VALUE_STUDIO_REFERENCE_IDS.opportunityId,
    caseId: VALUE_STUDIO_REFERENCE_IDS.caseId,
    modelVersion: VALUE_STUDIO_REFERENCE_IDS.modelVersion,
    updatedAt: FIXTURE_NOW,
    account: { name: "Acme Manufacturing" },
    opportunity: {
      opportunityId: VALUE_STUDIO_REFERENCE_IDS.opportunityId,
      arr: { amount: 1_200_000, currency: "USD" },
      decisionDate: "2026-09-12",
      champion: { principalId: "principal_r_chen", displayName: "R. Chen" },
    },
    economics: {
      annualBenefit: {
        amount: 720_000,
        currency: "USD",
        governanceLabel: "PROVISIONAL",
      },
      programCost: null,
      roi: null,
      formulaId: "formula_downtime_benefit_v3",
      formulaDisplay: "(400 − 340) × 12,000 USD = 720,000 USD/year",
    },
    governance: {
      primaryBlockerId: VALUE_STUDIO_REFERENCE_IDS.decisionId,
      publicationState: "BLOCKED",
      unresolvedDecisionIds: ["DISP-01", "DISP-02"],
      validationState: "Pending finance validation",
      approvalState: "Not approved",
    },
    allowedActions: [
      VALUE_STUDIO_ACTIONS.decisionSubmit,
      VALUE_STUDIO_ACTIONS.decisionEdit,
      VALUE_STUDIO_ACTIONS.decisionDefer,
      VALUE_STUDIO_ACTIONS.evidenceView,
    ],
    ...overrides,
  };
}

// ── Journey (contract §9.3) ──────────────────────────────────────────────────

export function makeJourneyProjection(
  overrides: Partial<JourneyProjection> = {},
): JourneyProjection {
  return {
    currentStage: "review",
    stages: [
      { stage: "scope", state: "completed" },
      { stage: "discover", state: "completed" },
      { stage: "validate", state: "completed" },
      { stage: "model", state: "completed" },
      { stage: "review", state: "current", detail: "CFO validation pending" },
      { stage: "deliver", state: "upcoming" },
      { stage: "realize", state: "upcoming" },
    ],
    ...overrides,
  };
}

// ── Mission projection (contract §7.2) ───────────────────────────────────────

export function makeMissionProjection(
  overrides: Partial<MissionProjection> = {},
): MissionProjection {
  return {
    missionId: VALUE_STUDIO_REFERENCE_IDS.missionId,
    caseId: VALUE_STUDIO_REFERENCE_IDS.caseId,
    version: 7,
    status: "EXECUTING",
    title: "Prepare Acme for CFO validation",
    coordinationMode: "DELEGATED",
    autonomySummary: "SUPERVISED",
    completedActionCount: 6,
    totalActionCount: 9,
    nextAction: {
      title: "Rebuild CFO briefing from model VM-12",
      status: "QUEUED",
    },
    pendingDecisionCount: 2,
    activeArtifactIds: [VALUE_STUDIO_REFERENCE_IDS.patchArtifactId],
    latestEventCursor: "cursor_evt_109",
    allowedActions: [VALUE_STUDIO_ACTIONS.missionPause, VALUE_STUDIO_ACTIONS.steerFlo],
    ...overrides,
  };
}

// ── Proposed model patch (contract §9.5) ─────────────────────────────────────

export function makePatchProjection(
  overrides: Partial<ModelPatchProjection> = {},
): ModelPatchProjection {
  return {
    artifactId: VALUE_STUDIO_REFERENCE_IDS.patchArtifactId,
    modelVersion: VALUE_STUDIO_REFERENCE_IDS.modelVersion,
    title: "Proposed model patch — VM-12",
    items: [
      {
        patchItemId: "patch_item_1",
        order: 1,
        summary: "Resolve working target to 340 hours",
        status: "proposed",
        affectedObjectIds: ["driver_downtime_target"],
        evidenceIds: ["EV-1001", "EV-1002"],
      },
      {
        patchItemId: "patch_item_2",
        order: 2,
        summary: "Keep 280 hours as upside scenario only",
        status: "proposed",
        affectedObjectIds: ["branch_upside_280"],
        evidenceIds: ["EV-1001"],
      },
      {
        patchItemId: "patch_item_3",
        order: 3,
        summary: "Recalculate downtime benefit to 720,000 USD",
        status: "pending",
        affectedObjectIds: ["metric_annual_benefit"],
        evidenceIds: ["EV-1003"],
      },
      {
        patchItemId: "patch_item_4",
        order: 4,
        summary: "Exclude FTE productivity from canonical total",
        status: "completed",
        affectedObjectIds: ["metric_fte_productivity"],
        evidenceIds: ["EV-1002"],
      },
      {
        patchItemId: "patch_item_5",
        order: 5,
        summary: "Regenerate CFO briefing and synchronize deliverables",
        status: "blocked",
        affectedObjectIds: ["deliverable_cfo_briefing"],
        evidenceIds: [],
      },
    ],
    ...overrides,
  };
}

// ── Branch comparison (contract §9.7) ────────────────────────────────────────

export function makeBranchComparisonProjection(
  overrides: Partial<BranchComparisonProjection> = {},
): BranchComparisonProjection {
  return {
    title: "Downtime target branches",
    horizonLabel: "12-month horizon",
    timingConventionLabel: "Annualized run-rate",
    status: "CALCULATED",
    branches: [
      {
        branchId: "branch_working_340",
        label: "Working target — 340 hours",
        status: "CALCULATED",
        recommended: true,
        evidenceState: "Evidence linked",
        metrics: [
          {
            label: "Annual downtime benefit",
            value: { amount: 720_000, currency: "USD" },
          },
        ],
      },
      {
        branchId: "branch_upside_280",
        label: "Upside scenario — 280 hours",
        status: "CALCULATED",
        recommended: false,
        evidenceState: "Evidence linked",
        metrics: [
          {
            label: "Annual downtime benefit",
            value: { amount: 1_440_000, currency: "USD" },
          },
        ],
      },
    ],
    ...overrides,
  };
}

// ── Evidence references (contract §7.3 / §9.10) ──────────────────────────────

export function makeEvidenceReferences(): readonly EvidenceReference[] {
  return [
    {
      evidenceId: "EV-1001",
      sourceType: "Telemetry export",
      sourceTitle: "Downtime telemetry export FY-2026",
      excerpt:
        "Aggregated line-level downtime totals 400 hours per year across 14 packaging lines.",
      capturedAt: EVIDENCE_CAPTURED.telemetry,
      traceabilityState: "Fully traced",
      validationState: "Validated",
      approvalState: "Approved for modeling",
      affectedObjectIds: ["driver_downtime_target"],
      restricted: false,
    },
    {
      evidenceId: "EV-1002",
      sourceType: "Time study",
      sourceTitle: "Line 4 changeover time study",
      excerpt:
        "Observed changeover losses support a 340-hour working target with current staffing.",
      capturedAt: EVIDENCE_CAPTURED.timeStudy,
      traceabilityState: "Fully traced",
      validationState: "Pending validation",
      approvalState: "Not approved",
      affectedObjectIds: ["driver_downtime_target", "metric_fte_productivity"],
      restricted: false,
    },
    {
      evidenceId: "EV-1003",
      sourceType: "Finance workbook",
      sourceTitle: "Downtime cost basis workbook",
      excerpt: "",
      capturedAt: EVIDENCE_CAPTURED.financeWorkbook,
      traceabilityState: "Partially traced",
      validationState: "Pending finance validation",
      approvalState: "Restricted",
      affectedObjectIds: ["metric_annual_benefit"],
      restricted: true,
    },
  ];
}

// ── Decision projection (contract §7.3, DISP-01) ─────────────────────────────

export function makeDecisionProjection(
  overrides: Partial<DecisionRequestProjection> = {},
): DecisionRequestProjection {
  return {
    decisionId: VALUE_STUDIO_REFERENCE_IDS.decisionId,
    decisionVersion: 3,
    missionId: VALUE_STUDIO_REFERENCE_IDS.missionId,
    caseId: VALUE_STUDIO_REFERENCE_IDS.caseId,
    modelVersion: VALUE_STUDIO_REFERENCE_IDS.modelVersion,
    status: "OPEN",
    title: "Resolve downtime target conflict",
    reasonForEscalation:
      "Working target (340 hours/year) conflicts with the upside scenario (280 hours/year). Selecting the working target changes governed economics and requires human authority.",
    currentWorkingValue: { value: 340, unit: "hours/year" },
    alternative: {
      value: 280,
      unit: "hours/year",
      proposedScope: "Upside scenario only",
    },
    evidence: makeEvidenceReferences(),
    governance: {
      traceability: "Full lineage to telemetry export EVT-4419",
      validation: "Pending finance validation",
      approval: "Not approved",
      economicInclusion: "In the 720k case? Yes — working target drives the canonical benefit.",
      requiredAuthority: "Value Engineer or above",
    },
    sensitivity: {
      display: "±20 hours moves annual benefit by ±240,000 USD",
    },
    calculatedImpact: {
      workingAnnualBenefit: { amount: 720_000, currency: "USD" },
      alternativeAnnualBenefit: { amount: 1_440_000, currency: "USD" },
    },
    recommendation:
      "Accept the working target of 340 hours/year and retain 280 hours/year as an upside scenario.",
    escalationDetail: {
      trigger: "Working target and upside scenario disagree on the downtime target.",
      attemptedWork:
        "Flo requested deterministic reconciliation from calculation service svc-calc-88.",
      stoppingBoundary:
        "Changing the working target alters governed economics; Flo lacks authority to resolve it.",
      recommendedNextAction:
        "Human review of DISP-01 with evidence pack EV-1001 through EV-1003.",
    },
    affectedObjectIds: ["driver_downtime_target", "metric_annual_benefit"],
    allowedActions: [
      VALUE_STUDIO_ACTIONS.decisionSubmit,
      VALUE_STUDIO_ACTIONS.decisionEdit,
      VALUE_STUDIO_ACTIONS.decisionDefer,
      VALUE_STUDIO_ACTIONS.evidenceView,
    ],
    ...overrides,
  };
}

// ── Activity events (contract §7.4 / §9.12) ──────────────────────────────────

export function makeActivityEvents(): readonly MissionActivityEvent[] {
  const missionId = VALUE_STUDIO_REFERENCE_IDS.missionId;
  const caseId = VALUE_STUDIO_REFERENCE_IDS.caseId;
  return [
    {
      eventId: "evt_101",
      missionId,
      caseId,
      sequence: 101,
      occurredAt: "2026-08-24T09:12:00.000Z",
      actorType: "SYSTEM",
      actorDisplayName: "ValueOS",
      eventType: "mission.created",
      status: "COMPLETED",
      summary: "Mission created from case case_acme_opp1842.",
      objectIds: [caseId],
      correlationId: "corr_mission_204_01",
      reversible: false,
      allowedActions: [],
    },
    {
      eventId: "evt_102",
      missionId,
      caseId,
      sequence: 102,
      occurredAt: "2026-08-24T09:14:00.000Z",
      actorType: "AGENT",
      actorDisplayName: "Flo",
      eventType: "context.loaded",
      status: "COMPLETED",
      summary: "Loaded account context and model VM-12.",
      objectIds: [caseId, "model_vm12"],
      modelVersion: "VM-12",
      correlationId: "corr_mission_204_02",
      reversible: false,
      allowedActions: [],
    },
    {
      eventId: "evt_103",
      missionId,
      caseId,
      sequence: 103,
      occurredAt: "2026-08-24T09:31:00.000Z",
      actorType: "AGENT",
      actorDisplayName: "Flo",
      eventType: "telemetry.baselined",
      status: "COMPLETED",
      summary: "Baselined downtime at 400 hours/year from telemetry export EVT-4419.",
      objectIds: ["EV-1001"],
      correlationId: "corr_mission_204_03",
      reversible: false,
      allowedActions: [],
    },
    {
      eventId: "evt_104",
      missionId,
      caseId,
      sequence: 104,
      occurredAt: "2026-08-24T09:48:00.000Z",
      actorType: "AGENT",
      actorDisplayName: "Flo",
      eventType: "calculation.requested",
      status: "FAILED",
      summary: "Deterministic benefit calculation failed: calculation service timeout (attempt 1).",
      objectIds: ["metric_annual_benefit"],
      correlationId: "corr_mission_204_04",
      reversible: false,
      allowedActions: [],
    },
    {
      eventId: "evt_105",
      missionId,
      caseId,
      sequence: 105,
      occurredAt: "2026-08-24T09:49:00.000Z",
      actorType: "AGENT",
      actorDisplayName: "Flo",
      eventType: "calculation.requested",
      status: "RETRIED",
      summary: "Retried deterministic calculation with unchanged inputs.",
      objectIds: ["metric_annual_benefit"],
      correlationId: "corr_mission_204_04",
      reversible: true,
      allowedActions: [],
    },
    {
      eventId: "evt_106",
      missionId,
      caseId,
      sequence: 106,
      occurredAt: "2026-08-24T09:50:00.000Z",
      actorType: "SYSTEM",
      actorDisplayName: "Calculation service",
      eventType: "calculation.completed",
      status: "COMPLETED",
      summary: "Calculation svc-calc-88 returned working annual benefit 720,000 USD/year.",
      objectIds: ["metric_annual_benefit"],
      modelVersion: "VM-12",
      correlationId: "corr_mission_204_04",
      reversible: false,
      allowedActions: [],
    },
    {
      eventId: "evt_107",
      missionId,
      caseId,
      sequence: 107,
      occurredAt: "2026-08-24T10:22:00.000Z",
      actorType: "AGENT",
      actorDisplayName: "Flo",
      eventType: "narrative.drafted",
      status: "COMPLETED",
      summary: "Drafted CFO narrative against model VM-12.",
      objectIds: ["deliverable_cfo_briefing"],
      correlationId: "corr_mission_204_05",
      reversible: false,
      allowedActions: [],
    },
    {
      eventId: "evt_108",
      missionId,
      caseId,
      sequence: 108,
      occurredAt: "2026-08-24T11:05:00.000Z",
      actorType: "AGENT",
      actorDisplayName: "Flo",
      eventType: "governance.checked",
      status: "COMPLETED",
      summary: "Policy check complete: publication remains blocked pending decision DISP-01.",
      objectIds: ["DISP-01"],
      correlationId: "corr_mission_204_06",
      reversible: false,
      allowedActions: [],
    },
    {
      eventId: "evt_109",
      missionId,
      caseId,
      sequence: 109,
      occurredAt: "2026-08-24T11:06:00.000Z",
      actorType: "AGENT",
      actorDisplayName: "Flo",
      eventType: "decision.requested",
      status: "WAITING",
      summary:
        "Conflict between working target (340 hours/year) and upside scenario (280 hours/year) requires human decision DISP-01.",
      objectIds: ["DISP-01"],
      correlationId: "corr_mission_204_07",
      reversible: false,
      allowedActions: [],
    },
  ];
}

// ── Composite projection ─────────────────────────────────────────────────────

export function makeValueStudioProjection(
  overrides: Partial<ValueStudioProjection> = {},
): ValueStudioProjection {
  return {
    projectionVersion: "vsp_vm12_0007",
    etag: "W/\"vsp_vm12_0007\"",
    generatedAt: FIXTURE_NOW,
    case: makeCaseProjection(),
    journey: makeJourneyProjection(),
    mission: makeMissionProjection(),
    patch: makePatchProjection(),
    decision: makeDecisionProjection(),
    branchComparison: makeBranchComparisonProjection(),
    activity: makeActivityEvents(),
    activeLens: "canonical",
    partial: null,
    stale: null,
    ...overrides,
  };
}

// ── Named fixture states (Slice-1 required state coverage) ───────────────────

/**
 * The ten named states required by the delivery contract. The default state is
 * `blocked` — the reference economic state of §1.4, where publication is
 * governance-blocked behind DISP-01.
 */
export const VALUE_STUDIO_FIXTURE_NAMES = [
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
] as const;

export type ValueStudioFixtureName = (typeof VALUE_STUDIO_FIXTURE_NAMES)[number];

export const DEFAULT_VALUE_STUDIO_FIXTURE: ValueStudioFixtureName = "blocked";

export function isValueStudioFixtureName(value: string | null): value is ValueStudioFixtureName {
  return (
    value !== null &&
    (VALUE_STUDIO_FIXTURE_NAMES as readonly string[]).includes(value)
  );
}

export interface ValueStudioFixtureResult {
  readonly name: ValueStudioFixtureName;
  readonly view: ValueStudioViewState;
}

/** DISP-01 resolved; unrelated finance blocker remains (FE-DEC-006, FE-SUC-004). */
function makeResolvedButFinanceBlockedProjection(): ValueStudioProjection {
  return makeValueStudioProjection({
    case: makeCaseProjection({
      governance: {
        primaryBlockerId: "FIN-02",
        publicationState: "BLOCKED",
        unresolvedDecisionIds: ["FIN-02"],
        validationState: "Pending finance validation",
        approvalState: "Not approved",
      },
    }),
    mission: makeMissionProjection({ pendingDecisionCount: 1 }),
    decision: makeDecisionProjection({
      status: "RESOLVED",
      allowedActions: [VALUE_STUDIO_ACTIONS.evidenceView],
      resolution: {
        resolvedAt: "2026-08-24T13:58:00.000Z",
        resolvedByDisplayName: "R. Chen",
        outcomeLabel: "Working target accepted",
        summary:
          "Working downtime target set to 340 hours/year; 280 hours/year retained as upside scenario. Finance validation and program-cost approval remain open.",
      },
    }),
    activity: [
      ...makeActivityEvents(),
      {
        eventId: "evt_110",
        missionId: VALUE_STUDIO_REFERENCE_IDS.missionId,
        caseId: VALUE_STUDIO_REFERENCE_IDS.caseId,
        sequence: 110,
        occurredAt: "2026-08-24T13:58:00.000Z",
        actorType: "HUMAN",
        actorDisplayName: "R. Chen",
        eventType: "decision.resolved",
        status: "COMPLETED",
        summary: "DISP-01 resolved: accepted working target of 340 hours/year.",
        objectIds: ["DISP-01"],
        modelVersion: "VM-12",
        correlationId: "corr_mission_204_08",
        reversible: false,
        allowedActions: [],
      },
    ],
  });
}

export function getValueStudioFixture(name: ValueStudioFixtureName): ValueStudioFixtureResult {
  switch (name) {
    case "loading":
      return { name, view: { kind: "loading" } };

    case "blocked":
      // Reference state per contract §1.4: publication blocked behind DISP-01.
      return { name, view: { kind: "ready", projection: makeValueStudioProjection() } };

    case "empty":
      return {
        name,
        view: {
          kind: "empty",
          reason:
            "No active mission for this opportunity.\n\nFlo is monitoring the case. " +
            "Start a preparation mission or open the latest value model.",
          projection: makeValueStudioProjection({
            mission: null,
            patch: null,
            decision: null,
            activity: [],
            branchComparison: makeBranchComparisonProjection({
              status: "AWAITING_AUTHORITATIVE_CALCULATION",
              branches: [],
            }),
          }),
        },
      };

    case "partial":
      // Contract §11.4 example: case and decision load; the activity stream fails.
      return {
        name,
        view: {
          kind: "partial",
          projection: makeValueStudioProjection({
            activity: [],
            partial: {
              unavailableSections: ["activity"],
              reasons: {
                activity:
                  "Mission event stream unavailable (correlation corr_fixture_partial_01).",
              },
            },
          }),
        },
      };

    case "error":
      return {
        name,
        view: {
          kind: "error",
          message: "The value case could not be loaded.",
          correlationId: "corr_fixture_error_01",
          retryable: true,
        },
      };

    case "offline":
      return {
        name,
        view: {
          kind: "offline",
          projection: makeValueStudioProjection(),
          lastSyncedAt: FIXTURE_NOW,
        },
      };

    case "stale":
      return {
        name,
        view: {
          kind: "stale",
          projection: makeValueStudioProjection({
            stale: {
              reason:
                "The case changed on the server while this view was open. " +
                "Submissions are paused until the latest projection loads.",
              expectedModelVersion: "VM-12",
              currentModelVersion: "VM-13",
              expectedDecisionVersion: 3,
              currentDecisionVersion: 4,
            },
          }),
        },
      };

    case "unauthorized":
      // No protected body data in this state (contract §8.1).
      return {
        name,
        view: {
          kind: "unauthorized",
          reason: "forbidden",
          message:
            "You do not have access to this value case. " +
            "Request access from the account owner or your tenant administrator.",
        },
      };

    case "resolved-decision-but-still-finance-blocked":
      return {
        name,
        view: { kind: "ready", projection: makeResolvedButFinanceBlockedProjection() },
      };

    case "static-renderer-fallback":
      return {
        name,
        view: {
          kind: "ready",
          projection: makeValueStudioProjection({
            activeLens: "cfo",
            generativeUiFallback: {
              componentName: "LensRenderer:cfo",
              failureClass: "RENDER_ERROR",
            },
          }),
        },
      };
  }
}
