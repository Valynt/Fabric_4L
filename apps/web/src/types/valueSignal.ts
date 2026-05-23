/**
 * Canonical ValueSignal types for the L2.5 Signal Refinery.
 *
 * These types mirror the backend Pydantic model in
 * packages/shared/src/value_fabric/shared/models/value_signal.py
 * and the JSON Schema contract in contracts/value-signal.json.
 *
 * SignalCard is a UI-only projection — not the domain model.
 */

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type ValueSignalType =
  | "pain"
  | "opportunity"
  | "risk"
  | "expansion"
  | "renewal"
  | "cost_saving"
  | "revenue_uplift"
  | "efficiency"
  | "compliance"
  | "strategic_priority";

export type ValueSignalLifecycleState =
  | "draft"
  | "extracted"
  | "validated"
  | "rejected"
  | "promoted"
  | "expired"
  | "superseded";

export type SignalImpactArea = "revenue" | "cost" | "risk" | "strategic";

export type ProvenanceExtractor = "human" | "ai" | "system";

// ---------------------------------------------------------------------------
// Sub-models
// ---------------------------------------------------------------------------

export interface ValueSignalEvidence {
  id: string;
  source_ref: string;
  excerpt?: string;
  url?: string;
  document_id?: string;
  confidence: number;
  relevance_score?: number;
}

export interface ValueSignalProvenance {
  extractor: ProvenanceExtractor;
  method: string;
  model?: string;
  run_id?: string;
  source_system?: string;
  extracted_at: string;
}

// ---------------------------------------------------------------------------
// Core domain model
// ---------------------------------------------------------------------------

export interface ValueSignal {
  // MVP-required
  id: string;
  tenant_id: string;
  account_id: string;
  type: ValueSignalType;
  content: string;
  confidence: number;
  trust_score: number;
  lifecycle_state: ValueSignalLifecycleState;
  evidence: ValueSignalEvidence[];
  provenance: ValueSignalProvenance;
  source_refs: string[];
  created_at: string;
  updated_at: string;

  // Optional enrichments
  opportunity_id?: string;
  value_driver_id?: string;
  stakeholder_id?: string;
  persona?: string;
  industry?: string;
  impact_area?: SignalImpactArea;
  estimated_value?: number;
  currency?: string;
  time_horizon?: string;
  validation_notes?: string;
  reviewer_id?: string;
  expires_at?: string;
  supersedes_signal_id?: string;
  related_signal_ids?: string[];
}

// ---------------------------------------------------------------------------
// UI projection — derived from ValueSignal, not the source of truth
// ---------------------------------------------------------------------------

export interface SignalCard {
  id: string;
  /** Truncated content used as display name */
  name: string;
  /** Human-readable label derived from type */
  category: string;
  confidence: number;
  trust_score: number;
  /** Derived from impact_area + estimated_value */
  impact: string;
  lifecycle_state: ValueSignalLifecycleState;
  /** Number of evidence items */
  evidence_count: number;
  /** e.g. "AI · llm_extraction" */
  provenance_label: string;
  review_status: "unreviewed" | "approved" | "rejected" | "pending_review";
  review_notes?: string;
  reviewed_at?: string;
  reviewed_by?: string;
  validation_notes?: string;
}

// ---------------------------------------------------------------------------
// API request/response types
// ---------------------------------------------------------------------------

export interface ValueSignalCreate {
  account_id: string;
  type: ValueSignalType;
  content: string;
  confidence: number;
  trust_score?: number;
  lifecycle_state?: ValueSignalLifecycleState;
  evidence?: ValueSignalEvidence[];
  provenance: ValueSignalProvenance;
  source_refs?: string[];
  opportunity_id?: string;
  value_driver_id?: string;
  stakeholder_id?: string;
  persona?: string;
  industry?: string;
  impact_area?: SignalImpactArea;
  estimated_value?: number;
  currency?: string;
  time_horizon?: string;
}

export interface ValueSignalUpdate {
  lifecycle_state?: ValueSignalLifecycleState;
  validation_notes?: string;
  reviewer_id?: string;
  impact_area?: SignalImpactArea;
  estimated_value?: number;
  currency?: string;
  time_horizon?: string;
  value_driver_id?: string;
  expires_at?: string;
  supersedes_signal_id?: string;
  related_signal_ids?: string[];
}

export interface SignalReviewRequest {
  status: "validated" | "rejected";
  notes?: string;
}

export interface SignalPromoteRequest {
  value_path_category: "revenue_uplift" | "cost_savings" | "risk_reduction" | "blended";
  value_driver_id?: string;
}

/** A single raw signal payload from L2 extraction, passed to the /refine endpoint. */
export interface RawSignalInput {
  account_id: string;
  type?: string;
  content: string;
  confidence: number;
  evidence?: ValueSignalEvidence[];
  provenance?: Partial<ValueSignalProvenance>;
  source_refs?: string[];
}

export interface SignalRefineRequest {
  account_id: string;
  /** Preferred: actual L2 extraction payloads to refine. */
  raw_signals?: RawSignalInput[];
  /** Backward-compatible fallback. Produces synthetic content — avoid in production. */
  source_refs?: string[];
  extraction_run_id?: string;
}

export interface ValueSignalListResponse {
  items: ValueSignal[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TYPE_LABELS: Record<ValueSignalType, string> = {
  pain: "Pain",
  opportunity: "Opportunity",
  risk: "Risk",
  expansion: "Expansion",
  renewal: "Renewal",
  cost_saving: "Cost Saving",
  revenue_uplift: "Revenue Uplift",
  efficiency: "Efficiency",
  compliance: "Compliance",
  strategic_priority: "Strategic Priority",
};

export function signalTypeLabel(type: ValueSignalType): string {
  return TYPE_LABELS[type] ?? type;
}

export function toSignalCard(signal: ValueSignal): SignalCard {
  const name =
    signal.content.length > 80
      ? signal.content.slice(0, 77) + "..."
      : signal.content;

  const impact = signal.impact_area
    ? signal.estimated_value
      ? `${signal.impact_area} · $${signal.estimated_value.toLocaleString()}${signal.currency ? " " + signal.currency : ""}`
      : signal.impact_area
    : "Unknown";

  const provenanceLabel = `${signal.provenance.extractor} · ${signal.provenance.method}`;

  const reviewStatus: SignalCard["review_status"] =
    signal.lifecycle_state === "validated"
      ? "approved"
      : signal.lifecycle_state === "rejected"
        ? "rejected"
        : signal.lifecycle_state === "promoted"
          ? "approved"
          : "unreviewed";

  return {
    id: signal.id,
    name,
    category: signalTypeLabel(signal.type),
    confidence: Math.round(signal.confidence * 100),
    trust_score: Math.round(signal.trust_score * 100),
    impact,
    lifecycle_state: signal.lifecycle_state,
    evidence_count: signal.evidence.length,
    provenance_label: provenanceLabel,
    review_status: reviewStatus,
    validation_notes: signal.validation_notes,
  };
}
