/**
 * Value Studio (mission-led) — typed intent preview builder.
 *
 * Contract: FE-VOS-STUDIO-001 §9.9 / FE-INTENT-001. The preview is generated
 * from the typed command plus the server projection — never free-form model
 * text. Every value interpolated here comes from the decision projection.
 */

import type { DecisionIntentPreviewContent, DecisionRequestProjection } from "./types";

const ACCEPT_WILL_NOT: readonly string[] = [
  "approve a program cost;",
  "calculate ROI if cost is unavailable;",
  "publish a deliverable;",
  "clear unrelated blockers.",
];

export function buildAcceptRecommendationPreview(
  decision: DecisionRequestProjection,
): DecisionIntentPreviewContent {
  const working = `${decision.currentWorkingValue.value} ${decision.currentWorkingValue.unit}`;
  const alternative = `${decision.alternative.value} ${decision.alternative.unit}`;
  return {
    commandType: "working_target.accept",
    expectedModelVersion: decision.modelVersion,
    expectedDecisionVersion: decision.decisionVersion,
    decisionId: decision.decisionId,
    payload: {
      kind: "accept",
      workingValue: decision.currentWorkingValue.value,
      workingUnit: decision.currentWorkingValue.unit,
      alternativeValue: decision.alternative.value,
      alternativeUnit: decision.alternative.unit,
    },
    will: [
      `set the working downtime target to ${working};`,
      `retain ${alternative} as an upside scenario;`,
      "request deterministic recalculation;",
      `resume ${decision.missionId} from its waiting checkpoint.`,
    ],
    willNot: ACCEPT_WILL_NOT,
  };
}

export interface EditDecisionDraft {
  readonly workingHours: number;
  readonly alternativeHours?: number;
  readonly alternativeScope?: string;
  readonly rationale: string;
}

export function buildEditDecisionPreview(
  decision: DecisionRequestProjection,
  draft: EditDecisionDraft,
): DecisionIntentPreviewContent {
  const workingUnit = decision.currentWorkingValue.unit;
  const will: string[] = [`set the working downtime target to ${draft.workingHours} ${workingUnit};`];
  if (typeof draft.alternativeHours === "number") {
    const scope = draft.alternativeScope ?? decision.alternative.proposedScope;
    will.push(`set the alternative to ${draft.alternativeHours} ${decision.alternative.unit} (${scope});`);
  }
  will.push("record the supplied rationale on the decision;", "request deterministic recalculation;");
  return {
    commandType: "decision.edit",
    expectedModelVersion: decision.modelVersion,
    expectedDecisionVersion: decision.decisionVersion,
    decisionId: decision.decisionId,
    payload: {
      kind: "edit",
      workingValue: draft.workingHours,
      workingUnit,
      alternativeValue: draft.alternativeHours,
      alternativeUnit: typeof draft.alternativeHours === "number" ? decision.alternative.unit : undefined,
      alternativeScope: draft.alternativeScope ?? decision.alternative.proposedScope,
      rationale: draft.rationale,
    },
    will,
    willNot: ACCEPT_WILL_NOT,
  };
}

export function buildDeferDecisionPreview(
  decision: DecisionRequestProjection,
  input: { readonly ownerDisplayName: string; readonly dueAt: string; readonly reason: string },
): DecisionIntentPreviewContent {
  return {
    commandType: "decision.defer",
    expectedModelVersion: decision.modelVersion,
    expectedDecisionVersion: decision.decisionVersion,
    decisionId: decision.decisionId,
    payload: {
      kind: "defer",
      ownerDisplayName: input.ownerDisplayName,
      dueAt: input.dueAt,
      reason: input.reason,
    },
    will: [
      `defer ${decision.decisionId} to ${input.ownerDisplayName} until ${input.dueAt};`,
      "pause dependent artifact regeneration until the due date;",
      `record the defer reason: ${input.reason};`,
    ],
    willNot: [
      "change the working downtime target;",
      ...ACCEPT_WILL_NOT,
    ],
  };
}
