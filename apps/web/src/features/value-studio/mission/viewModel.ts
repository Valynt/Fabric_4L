/**
 * Value Studio (mission-led) — projection → view-model mapping.
 *
 * Pure functions only. Mapping never fabricates values: missing data maps to
 * explicit contract copy ("Pending", "Not yet calculable") rather than zero
 * (FE-IMP-004). Unit tests cover currency/null formatting and mapping.
 */

import type {
  AudienceLens,
  EconomicGovernanceLabel,
  GovernedMoney,
  GovernedRatio,
  JourneyStageId,
  MissionAutonomySummary,
  MissionCoordinationMode,
  MissionStatus,
  Money,
  PublicationState,
} from "./types";

// ── Money / ratio formatting (contract §1.4 display style) ───────────────────

const FULL_NUMBER_FORMATTER = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

/** "720,000 USD" — full precision, currency code suffix. */
export function formatMoneyFull(value: Money): string {
  return `${FULL_NUMBER_FORMATTER.format(value.amount)} ${value.currency}`;
}

/** Annual-benefit style: "720,000 USD/year". */
export function formatMoneyAnnual(value: Money): string {
  return `${formatMoneyFull(value)}/year`;
}

/** FE-IMP-002: null program cost renders "Pending", never zero. */
export function formatProgramCost(value: GovernedMoney | null): string {
  return value === null ? "Pending" : formatMoneyAnnual(value);
}

/** FE-IMP-003: null ROI renders "Not yet calculable", never zero. */
export function formatRoi(value: GovernedRatio | null): string {
  return value === null ? "Not yet calculable" : `${value.ratio.toFixed(2)}×`;
}

/** Governance label → display text (backend-owned label, FE-HDR-003). */
export const GOVERNANCE_LABEL_DISPLAY: Record<EconomicGovernanceLabel, string> = {
  PROVISIONAL: "Provisional",
  VALIDATED: "Validated",
  APPROVED: "Approved",
};

export function formatGovernanceLabel(label: EconomicGovernanceLabel): string {
  return GOVERNANCE_LABEL_DISPLAY[label];
}

// ── Enum → display maps (text always accompanies color, FE-A11Y-004) ─────────

export const LENS_DISPLAY: Record<AudienceLens, string> = {
  canonical: "Canonical",
  champion: "Champion",
  cfo: "CFO",
  technical: "Technical",
  executive: "Executive",
  qbr: "QBR",
};

export const JOURNEY_STAGE_DISPLAY: Record<JourneyStageId, string> = {
  scope: "Scope",
  discover: "Discover",
  validate: "Validate",
  model: "Model",
  review: "Review",
  deliver: "Deliver",
  realize: "Realize",
};

export const MISSION_STATUS_DISPLAY: Record<MissionStatus, string> = {
  PLANNING: "Planning",
  EXECUTING: "Executing",
  WAITING_FOR_HUMAN: "Waiting for you",
  PAUSING: "Pausing",
  PAUSED: "Paused",
  RESUMING: "Resuming",
  VERIFYING: "Verifying",
  COMPLETED: "Completed",
  MONITORING: "Monitoring",
  FAILED: "Failed",
};

export const COORDINATION_MODE_DISPLAY: Record<MissionCoordinationMode, string> = {
  BACKGROUND: "Background",
  COLLABORATIVE: "Collaborative",
  DELEGATED: "Delegated",
};

export const AUTONOMY_DISPLAY: Record<MissionAutonomySummary, string> = {
  APPROVAL_REQUIRED: "Approval required",
  SUPERVISED: "Supervised",
  WITHIN_POLICY: "Within policy",
};

export const PUBLICATION_STATE_DISPLAY: Record<PublicationState, string> = {
  BLOCKED: "Publication Blocked",
  PROVISIONAL: "Publication Provisional",
  READY_FOR_REVIEW: "Ready for review",
  APPROVED: "Approved for publication",
};

/** Deterministic ordering + dedupe for mission events (FE-ACT-007). */
export function orderActivityEvents<T extends { sequence: number; eventId: string }>(
  events: readonly T[],
): readonly T[] {
  const seen = new Set<string>();
  const deduped: T[] = [];
  for (const event of [...events].sort((a, b) => a.sequence - b.sequence)) {
    if (!seen.has(event.eventId)) {
      seen.add(event.eventId);
      deduped.push(event);
    }
  }
  return deduped;
}
