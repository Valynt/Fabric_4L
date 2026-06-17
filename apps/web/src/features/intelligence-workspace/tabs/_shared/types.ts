/**
 * Shared data shapes for the core value-case workspace views.
 *
 * These are intentionally permissive (most fields optional) so the screens
 * render whatever the case currently has — partial data on day one is expected
 * (Signal → Driver → Evidence → Stakeholder fills in over time).
 */

export type SignalCategory =
  | "pain"
  | "buying"
  | "risk"
  | "budget"
  | "stakeholder"
  | "timeline"
  | "competitive"
  | "metric";

export type SignalStatus =
  | "detected"
  | "accepted"
  | "rejected"
  | "promoted"
  | "assumption";

export interface WorkspaceSignal {
  id: string;
  title: string;
  type?: SignalCategory | string;
  source?: string;
  excerpt?: string;
  /** 0–1 or 0–100; normalised for display via toPercent(). */
  confidence?: number;
  status?: SignalStatus | string;
  relatedDriver?: string;
  relatedDriverId?: string;
  detectedAt?: string;
}

export interface WorkspaceDriver {
  id: string;
  name: string;
  /** Percentage contribution to the case (0–100). */
  contribution?: number;
  parentSignal?: string;
  linkedSignals?: string[];
  subDrivers?: string[];
  impactArea?: string;
  estimatedImpact?: string;
  valueLever?: string;
  neededInputs?: string[];
  readiness?: string;
}

export type VerificationState = "verified" | "partial" | "unverified";

export interface WorkspaceEvidenceItem {
  id: string;
  title: string;
  claim?: string;
  type?: string;
  source?: string;
  sourceLocation?: string;
  /** 0–100 match/relevance score. */
  matchScore?: number;
  /** 0–1 or 0–100; normalised for display via toPercent(). */
  confidence?: number;
  verification?: VerificationState | string;
  linkedDriver?: string;
  linkedSignals?: string[];
  excerpt?: string;
  usedInCase?: boolean;
}

export type StakeholderInfluence = "high" | "medium" | "low";

export interface WorkspaceStakeholder {
  id: string;
  name: string;
  title?: string;
  role?: string;
  influence?: StakeholderInfluence | string;
  position?: string;
  relationshipStrength?: string;
  priorities?: string[];
  objections?: string[];
  relevantSignals?: string[];
  linkedDriver?: string;
  nextAction?: string;
  engagementLevel?: StakeholderInfluence | string;
  evidenceSource?: string;
  quotes?: string[];
}
