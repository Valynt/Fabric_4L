/**
 * Value Studio (mission-led) — typed intent preview builder.
 *
 * Contract: FE-VOS-STUDIO-001 §9.9 / FE-INTENT-001. The preview is generated
 * from the typed command plus the server projection — never free-form model
 * text. Every value interpolated here comes from the decision projection.
 */

import type { DecisionIntentPreviewContent, DecisionRequestProjection } from "./types";

/** Static policy limits for the DISP-01 accept command (contract §9.9). */
const ACCEPT_WILL_NOT: readonly string[] = [
  "approve 12,000 USD/hour;",
  "approve program cost;",
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
  const unit = decision.currentWorkingValue.unit;
  const will: string[] = [`set the working downtime target to ${draft.workingHours} ${unit};`];
  if (typeof draft.alternativeHours === "number") {
    const scope = draft.alternativeScope ?? decision.alternative.proposedScope;
    will.push(`set the alternative to ${draft.alternativeHours} ${unit} (${scope});`);
  }
  will.push("record the supplied rationale on the decision;", "request deterministic recalculation;");
  return {
    commandType: "decision.edit",
    expectedModelVersion: decision.modelVersion,
    expectedDecisionVersion: decision.decisionVersion,
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
    will: [
      `defer ${decision.decisionId} to ${input.ownerDisplayName} until ${input.dueAt};`,
      "pause dependent artifact regeneration until the due date;",
    ],
    willNot: [
      "change the working downtime target;",
      ...ACCEPT_WILL_NOT,
    ],
  };
}
