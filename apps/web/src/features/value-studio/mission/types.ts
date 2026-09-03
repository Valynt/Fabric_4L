/**
 * Value Studio (mission-led) — typed, read-only projection contracts.
 *
 * Contract: FE-VOS-STUDIO-001 (docs/contracts/FE-VOS-STUDIO-001.md), §7.
 *
 * These types describe the authoritative server projection that the Value
 * Studio slice renders. The front end NEVER derives, recalculates, or
 * overwrites economic truth, mission state, authorization, or workflow
 * completion. View components receive projections; they must not own or
 * derive canonical domain state.
 *
 * Phase 1 note: projections are supplied by deterministic fixtures behind an
 * adapter seam (see `adapter.ts`). Phase 2 replaces the fixture adapter with a
 * TanStack Query projection adapter without changing these types.
 */

// ── Shared primitives ────────────────────────────────────────────────────────

/** RFC 3339 / ISO 8601 timestamp produced by the server. Never browser-generated. */
export type IsoDateTime = string;

/** Tenant-scoped identifier. */
export type TenantId = string;
export type AccountId = string;
export type OpportunityId = string;
export type CaseId = string;
export type MissionId = string;
export type DecisionId = string;
export type EventId = string;
export type EvidenceId = string;

/** Monetary amount in a explicit currency. Amount is a projection value. */
export interface Money {
  readonly amount: number;
  readonly currency: string;
}

/** Governance label attached by the backend to an economic value. */
export type EconomicGovernanceLabel = "PROVISIONAL" | "VALIDATED" | "APPROVED";

/** Economic value with its backend-assigned governance label. */
export interface GovernedMoney extends Money {
  readonly governanceLabel: EconomicGovernanceLabel;
}

/** Ratio value (e.g. ROI) with governance label. Null when not calculable. */
export interface GovernedRatio {
  readonly ratio: number;
  readonly governanceLabel: EconomicGovernanceLabel;
}

/** Publication lifecycle for customer-facing deliverables. */
export type PublicationState = "BLOCKED" | "PROVISIONAL" | "READY_FOR_REVIEW" | "APPROVED";

/** Audience lenses. Lens changes presentation depth/ordering only. */
export const AUDIENCE_LENSES = [
  "canonical",
  "champion",
  "cfo",
  "technical",
  "executive",
  "qbr",
] as const;
export type AudienceLens = (typeof AUDIENCE_LENSES)[number];

// ── Journey ──────────────────────────────────────────────────────────────────

/** Opportunity journey stages in canonical order. Status, not navigation. */
export const JOURNEY_STAGES = [
  "scope",
  "discover",
  "validate",
  "model",
  "review",
  "deliver",
  "realize",
] as const;
export type JourneyStageId = (typeof JOURNEY_STAGES)[number];

export type JourneyStageState = "completed" | "current" | "upcoming" | "blocked";

export interface JourneyStageStatus {
  readonly stage: JourneyStageId;
  readonly state: JourneyStageState;
  /** Position is derived from canonical order; the server may override display detail. */
  readonly detail?: string;
}

export interface JourneyProjection {
  readonly stages: readonly JourneyStageStatus[];
  readonly currentStage: JourneyStageId;
}

// ── Case projection (contract §7.1) ──────────────────────────────────────────

export interface ValueStudioCaseProjection {
  readonly tenantId: TenantId;
  readonly accountId: AccountId;
  readonly opportunityId: OpportunityId;
  readonly caseId: CaseId;
  readonly modelVersion: string;
  readonly updatedAt: IsoDateTime;

  readonly account: {
    readonly name: string;
  };

  readonly opportunity: {
    readonly opportunityId: OpportunityId;
    readonly arr: Money;
    readonly decisionDate: IsoDateTime;
    readonly champion: {
      readonly principalId?: string;
      readonly displayName: string;
    };
  };

  readonly economics: {
    readonly annualBenefit: GovernedMoney;
    readonly programCost: GovernedMoney | null;
    readonly roi: GovernedRatio | null;
    readonly formulaId: string;
    /** Server-rendered formula explanation, e.g. "(400 − 340) × $12,000 = $720,000 / yr". */
    readonly formulaDisplay: string;
  };

  readonly governance: {
    readonly primaryBlockerId: string | null;
    readonly publicationState: PublicationState;
    readonly unresolvedDecisionIds: readonly DecisionId[];
    readonly validationState: string;
    readonly approvalState: string;
  };

  readonly allowedActions: readonly string[];
}

// ── Mission projection (contract §7.2) ───────────────────────────────────────

export type MissionStatus =
  | "PLANNING"
  | "EXECUTING"
  | "WAITING_FOR_HUMAN"
  | "PAUSING"
  | "PAUSED"
  | "RESUMING"
  | "VERIFYING"
  | "COMPLETED"
  | "MONITORING"
  | "FAILED";

export type MissionCoordinationMode = "BACKGROUND" | "COLLABORATIVE" | "DELEGATED";
export type MissionAutonomySummary = "APPROVAL_REQUIRED" | "SUPERVISED" | "WITHIN_POLICY";

export interface MissionProjection {
  readonly missionId: MissionId;
  readonly caseId: CaseId;
  readonly version: number;
  readonly status: MissionStatus;
  readonly title: string;
  readonly coordinationMode: MissionCoordinationMode;
  readonly autonomySummary: MissionAutonomySummary;
  readonly completedActionCount: number;
  readonly totalActionCount: number;
  readonly nextAction: {
    readonly title: string;
    readonly status: string;
  } | null;
  readonly pendingDecisionCount: number;
  readonly activeArtifactIds: readonly string[];
  readonly latestEventCursor: string | null;
  readonly allowedActions: readonly string[];
}

// ── Proposed model patch artifact ────────────────────────────────────────────

export type ModelPatchItemStatus = "proposed" | "pending" | "completed" | "blocked";

export interface ModelPatchItem {
  readonly patchItemId: string;
  readonly order: number;
  readonly summary: string;
  readonly status: ModelPatchItemStatus;
  /** Objects (drivers, variables, artifacts) this item touches. */
  readonly affectedObjectIds: readonly string[];
  readonly evidenceIds: readonly EvidenceId[];
}

export interface ModelPatchProjection {
  readonly artifactId: string;
  readonly modelVersion: string;
  readonly title: string;
  readonly items: readonly ModelPatchItem[];
}

// ── Branch comparison ────────────────────────────────────────────────────────

export type BranchCalculationStatus = "CALCULATED" | "AWAITING_AUTHORITATIVE_CALCULATION";

export interface BranchMetric {
  /** Metric label supplied by the backend calculation projection. */
  readonly label: string;
  readonly value: Money;
}

export interface BranchComparisonBranch {
  readonly branchId: string;
  /** e.g. "3-month implementation" / "6-month implementation". */
  readonly label: string;
  readonly status: BranchCalculationStatus;
  readonly metrics: readonly BranchMetric[];
  readonly evidenceState: string;
  /** Shown only when the backend decision projection states a recommendation. */
  readonly recommended: boolean;
}

export interface BranchComparisonProjection {
  readonly title: string;
  /** Horizon and timing convention are explicit when values are calculated. */
  readonly horizonLabel: string | null;
  readonly timingConventionLabel: string | null;
  readonly branches: readonly BranchComparisonBranch[];
  readonly status: BranchCalculationStatus;
}

// ── Decision projection (contract §7.3) ──────────────────────────────────────

export type DecisionStatus =
  | "OPEN"
  | "SUBMITTING"
  | "RESOLVED"
  | "DEFERRED"
  | "REJECTED"
  | "STALE"
  | "CANCELLED";

export interface EvidenceReference {
  readonly evidenceId: EvidenceId;
  readonly sourceType: string;
  readonly sourceTitle: string;
  /** Safe summary or excerpt — never raw tenant-sensitive source content. */
  readonly excerpt: string;
  readonly capturedAt: IsoDateTime;
  readonly traceabilityState: string;
  readonly validationState: string;
  readonly approvalState: string;
  readonly affectedObjectIds: readonly string[];
  /** Present only when the backend authorizes rendering the excerpt. */
  readonly restricted: boolean;
}

export interface DecisionRequestProjection {
  readonly decisionId: DecisionId;
  readonly decisionVersion: number;
  readonly missionId: MissionId;
  readonly caseId: CaseId;
  readonly modelVersion: string;
  readonly status: DecisionStatus;

  readonly title: string;
  readonly reasonForEscalation: string;

  readonly currentWorkingValue: {
    readonly value: number;
    readonly unit: string;
  };

  readonly alternative: {
    readonly value: number;
    readonly unit: string;
    readonly proposedScope: string;
  };

  readonly evidence: readonly EvidenceReference[];

  readonly governance: {
    readonly traceability: string;
    readonly validation: string;
    readonly approval: string;
    /** Plain-language economic inclusion, e.g. "In the $720k case?". */
    readonly economicInclusion: string;
    readonly requiredAuthority: string;
  };

  readonly sensitivity: {
    readonly display: string;
  };

  readonly calculatedImpact: {
    readonly workingAnnualBenefit: Money;
    readonly alternativeAnnualBenefit: Money;
  };

  /** Flo's recommendation text, supplied by the backend decision packet. */
  readonly recommendation: string;
  /** Why Flo stopped: trigger, attempted work, stopping boundary, next action. */
  readonly escalationDetail: {
    readonly trigger: string;
    readonly attemptedWork: string;
    readonly stoppingBoundary: string;
    readonly recommendedNextAction: string;
  };
  readonly affectedObjectIds: readonly string[];
  readonly allowedActions: readonly string[];
  /**
   * Present only when the server projection reports a resolved decision.
   * The UI never infers resolution locally (FE-DEC-004) and never labels the
   * outcome "Locked" unless this payload carries that state (FE-DEC-005).
   */
  readonly resolution?: {
    readonly resolvedAt: IsoDateTime;
    readonly resolvedByDisplayName: string;
    readonly summary: string;
    readonly outcomeLabel: string;
  };
}

// ── Activity events (contract §7.4) ──────────────────────────────────────────

export type MissionActivityActorType = "HUMAN" | "AGENT" | "SYSTEM";
export type MissionActivityStatus = "STARTED" | "COMPLETED" | "WAITING" | "FAILED" | "RETRIED";

export interface MissionActivityEvent {
  readonly eventId: EventId;
  readonly missionId: MissionId;
  readonly caseId: CaseId;
  readonly sequence: number;
  /** Authoritative timestamp. The browser must never invent event time. */
  readonly occurredAt: IsoDateTime;
  readonly actorType: MissionActivityActorType;
  readonly actorDisplayName: string;
  readonly eventType: string;
  readonly status: MissionActivityStatus;
  /** Safe summary — no raw chain-of-thought, no unrestricted tool arguments. */
  readonly summary: string;
  readonly objectIds: readonly string[];
  readonly modelVersion?: string;
  readonly correlationId: string;
  readonly reversible: boolean;
  readonly allowedActions: readonly string[];
}

// ── Intent preview (typed command preview; contract §7.5 / §9.9) ─────────────

/** Static, typed preview of the DISP-01 accept-recommendation command. */
export interface DecisionIntentPreviewContent {
  readonly will: readonly string[];
  readonly willNot: readonly string[];
  readonly commandType: "working_target.accept" | "decision.edit" | "decision.defer";
  readonly expectedModelVersion: string;
  readonly expectedDecisionVersion: number;
}

// ── Composite page projection ────────────────────────────────────────────────

/** Metadata describing partially-available projection sections. */
export interface PartialDataMetadata {
  readonly unavailableSections: readonly ValueStudioSectionId[];
  readonly reasons: Readonly<Record<string, string>>;
}

/** Metadata describing a stale projection (server-side version drift). */
export interface StaleStateMetadata {
  readonly reason: string;
  readonly expectedModelVersion: string;
  readonly currentModelVersion: string;
  readonly expectedDecisionVersion?: number;
  readonly currentDecisionVersion?: number;
}

export type ValueStudioSectionId =
  | "header"
  | "journey"
  | "mission"
  | "patch"
  | "impact"
  | "branchComparison"
  | "decision"
  | "activity";

export interface ValueStudioProjection {
  readonly projectionVersion: string;
  readonly etag: string;
  readonly generatedAt: IsoDateTime;
  readonly case: ValueStudioCaseProjection;
  readonly journey: JourneyProjection;
  readonly mission: MissionProjection | null;
  readonly patch: ModelPatchProjection | null;
  readonly decision: DecisionRequestProjection | null;
  readonly branchComparison: BranchComparisonProjection;
  readonly activity: readonly MissionActivityEvent[];
  readonly activeLens: AudienceLens;
  readonly partial: PartialDataMetadata | null;
  readonly stale: StaleStateMetadata | null;
  /**
   * Set when a generative-UI surface failed and the server flagged a static
   * fallback (contract §11.4, FE-SUC-010). The affected lens renders the static
   * approved component plus a non-blocking notice.
   */
  readonly generativeUiFallback?: {
    readonly componentName: string;
    readonly failureClass: string;
  };
}

// ── Page view state (contract §8.1 + Slice-1 named states) ───────────────────

/**
 * The ten named states required by FE-VOS-STUDIO-001 are modeled explicitly so
 * that each is an intentional, testable rendering — never an accidental blank.
 */
export type ValueStudioViewState =
  | { readonly kind: "loading" }
  | { readonly kind: "ready"; readonly projection: ValueStudioProjection }
  | { readonly kind: "empty"; readonly reason: string; readonly projection: ValueStudioProjection }
  | {
      readonly kind: "partial";
      readonly projection: ValueStudioProjection;
    }
  | {
      readonly kind: "error";
      readonly message: string;
      readonly correlationId: string;
      readonly retryable: boolean;
    }
  | {
      readonly kind: "offline";
      readonly projection: ValueStudioProjection;
      readonly lastSyncedAt: IsoDateTime;
    }
  | {
      readonly kind: "stale";
      readonly projection: ValueStudioProjection;
    }
  | {
      readonly kind: "unauthorized";
      readonly reason: "unauthenticated" | "forbidden";
      readonly message: string;
    };

/** Allowed action identifiers used by Slice 1 fixtures (backend-owned in prod). */
export const VALUE_STUDIO_ACTIONS = {
  decisionSubmit: "decision.submit",
  decisionEdit: "decision.edit",
  decisionDefer: "decision.defer",
  evidenceView: "evidence.view",
  missionPause: "mission.pause",
  missionResume: "mission.resume",
  steerFlo: "mission.steer",
} as const;
