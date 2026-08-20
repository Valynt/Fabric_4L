/**
 * Value Case API Schemas (Zod Transport Validation)
 *
 * Validates untrusted transport payloads from API endpoints before passing to domain adapters.
 */
import { z } from "zod";

export class ValueCaseBoundaryError extends Error {
  readonly code:
    | "VALIDATION_FAILED"
    | "IDENTITY_MISMATCH"
    | "NETWORK_ERROR"
    | "MALFORMED_PAYLOAD"
    | "validation_failed"
    | "identity_mismatch"
    | "transport_error"
    | "unknown_error";
  readonly status?: number;
  readonly details?: unknown;
  readonly rawError?: unknown;

  constructor(
    message: string,
    code:
      | "VALIDATION_FAILED"
      | "IDENTITY_MISMATCH"
      | "NETWORK_ERROR"
      | "MALFORMED_PAYLOAD"
      | "validation_failed"
      | "identity_mismatch"
      | "transport_error"
      | "unknown_error" = "MALFORMED_PAYLOAD",
    statusOrDetails?: number | unknown,
    details?: unknown
  ) {
    super(message);
    this.name = "ValueCaseBoundaryError";
    this.code = code;
    if (typeof statusOrDetails === "number") {
      this.status = statusOrDetails;
      this.details = details;
      this.rawError = details;
    } else {
      this.status = undefined;
      this.details = statusOrDetails !== undefined ? statusOrDetails : details;
      this.rawError = this.details;
    }
  }
}

export function normalizeBoundaryError(error: unknown): ValueCaseBoundaryError {
  if (error instanceof ValueCaseBoundaryError) {
    return error;
  }
  if (error instanceof Error) {
    return new ValueCaseBoundaryError(
      error.message,
      "transport_error",
      500,
      error
    );
  }
  return new ValueCaseBoundaryError(
    typeof error === "string" ? error : "An unexpected error occurred",
    "unknown_error",
    500,
    error
  );
}

// ── Shared Sub-Schemas ────────────────────────────────────────────────────────

export const apiValueCaseSectionSchema = z.object({
  id: z.string().min(1),
  type: z.string().min(1).default("general"),
  title: z.string().min(1),
  content: z.string(),
  order: z.number().int().nonnegative().optional(),
});
export type ApiValueCaseSection = z.infer<typeof apiValueCaseSectionSchema>;

export const apiValueCaseStakeholderFramingSchema = z.object({
  persona: z.string().min(1),
  priorities: z.array(z.string()).optional(),
  pains: z.array(z.string()).optional(),
  decision_role: z.string().nullable().optional(),
});
export type ApiValueCaseStakeholderFraming = z.infer<typeof apiValueCaseStakeholderFramingSchema>;

export const apiRoiMetricsSchema = z.object({
  three_year_value: z.string().default(""),
  roi: z.string().default(""),
  payback: z.string().default(""),
});
export type ApiRoiMetrics = z.infer<typeof apiRoiMetricsSchema>;

export const apiValueCaseArtifactsInputSchema = z.object({
  account_id: z.string().min(1),
  account_name: z.string().default(""),
  stakeholders: z.array(z.string()).default([]),
  accepted_evidence: z.array(z.string()).default([]),
  scenario_assumptions: z.array(z.string()).default([]),
  roi_metrics: apiRoiMetricsSchema.default({
    three_year_value: "",
    roi: "",
    payback: "",
  }),
  risk_notes: z.array(z.string()).default([]),
});
export type ApiValueCaseArtifactsInput = z.infer<typeof apiValueCaseArtifactsInputSchema>;

export const apiValueCaseContentSchema = z.object({
  inputs: apiValueCaseArtifactsInputSchema.optional(),
  selected_scenario_id: z.string().nullable().optional(),
  sections: z.array(apiValueCaseSectionSchema).default([]),
  assumption_ids: z.array(z.string()).default([]),
  evidence_ids: z.array(z.string()).default([]),
  stakeholder_framing: z.array(apiValueCaseStakeholderFramingSchema).default([]),
  claim_ids: z.array(z.string()).default([]),
  roi_snapshot: z.record(z.string(), z.unknown()).nullable().optional(),
});
export type ApiValueCaseContent = z.infer<typeof apiValueCaseContentSchema>;

export const valueCaseSectionSchema = apiValueCaseSectionSchema;
export const valueCaseArtifactsInputSchema = apiValueCaseArtifactsInputSchema;
export const valueCaseContentSchema = apiValueCaseContentSchema;
export const valueCaseStakeholderFramingSchema = apiValueCaseStakeholderFramingSchema;

export const apiBusinessCaseSchema = z.object({
  id: z.string().min(1),
  account_id: z.string().min(1),
  version: z.number().optional(),
  title: z.string().default("Untitled Value Case"),
  status: z.string().default("draft"),
  audit: z
    .object({
      created_at: z.string().datetime({ offset: true }).or(z.string().min(1)),
      updated_at: z.string().datetime({ offset: true }).or(z.string().min(1)),
    })
    .default(() => ({
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
  executive_summary: z.string().optional(),
  value_narrative: z.string().optional(),
  value_case: apiValueCaseContentSchema.optional(),
  assumptions: z.array(z.string()).default([]),
  risks: z.array(z.string()).default([]),
});
export type ApiBusinessCase = z.infer<typeof apiBusinessCaseSchema>;
export type ApiBusinessCaseDto = ApiBusinessCase;

export const apiValueCaseListSchema = z.array(apiBusinessCaseSchema);
export type ApiValueCaseList = z.infer<typeof apiValueCaseListSchema>;

export const apiAccountOpportunitySummarySchema = z.object({
  id: z.string().min(1),
  name: z.string().default(""),
  stage: z.string().optional(),
  target_close: z.string().optional(),
  amount: z.number().optional(),
});
export type ApiAccountOpportunitySummary = z.infer<typeof apiAccountOpportunitySummarySchema>;

export const apiAccountSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  industry: z.string().optional(),
  tier: z.string().optional(),
  status: z.string().optional(),
  opportunity_summary: apiAccountOpportunitySummarySchema.optional(),
});
export type ApiAccount = z.infer<typeof apiAccountSchema>;

// ── Validation Helpers ────────────────────────────────────────────────────────

export function parseApiBusinessCase(payload: unknown): ApiBusinessCase {
  const result = apiBusinessCaseSchema.safeParse(payload);
  if (!result.success) {
    throw new ValueCaseBoundaryError(
      "Failed to parse Value Case response payload from server",
      "MALFORMED_PAYLOAD",
      result.error.format()
    );
  }
  return result.data;
}

export function parseApiValueCaseList(payload: unknown): ApiBusinessCase[] {
  const rawList = Array.isArray(payload) ? payload : [];
  const result = apiValueCaseListSchema.safeParse(rawList);
  if (!result.success) {
    throw new ValueCaseBoundaryError(
      "Failed to parse Value Case list from server",
      "MALFORMED_PAYLOAD",
      result.error.format()
    );
  }
  return result.data;
}

export function parseApiAccount(payload: unknown): ApiAccount {
  const result = apiAccountSchema.safeParse(payload);
  if (!result.success) {
    throw new ValueCaseBoundaryError(
      "Failed to parse Account response from server",
      "MALFORMED_PAYLOAD",
      result.error.format()
    );
  }
  return result.data;
}
