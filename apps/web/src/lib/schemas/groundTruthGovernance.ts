import { z } from "zod";

const UnknownRecordSchema = z.record(z.string(), z.unknown());

export const TruthStatusSchema = z.enum([
  "proposed",
  "validated",
  "disputed",
  "rejected",
  "superseded",
  "expired",
]);

export const ClaimTypeSchema = z.enum([
  "cost_savings_baseline",
  "revenue_impact",
  "efficiency_gain",
  "risk_reduction",
  "compliance_requirement",
  "customer_outcome",
  "technical_capability",
  "market_benchmark",
  "persona_pain_point",
  "value_driver_metric",
  "other",
]);

export const TruthObjectSummarySchema = z.looseObject({
    id: z.string(),
    claim: z.string(),
    claim_type: ClaimTypeSchema,
    confidence: z.number(),
    status: TruthStatusSchema,
    maturity_level: z.number(),
    is_stale: z.boolean(),
    source_count: z.number().int().min(0),
    validated_by: z.string().nullable().optional(),
    freshness: z.string(),
    created_at: z.string(),
  });

export const TruthObjectListResponseSchema = z.looseObject({
    items: z.array(TruthObjectSummarySchema),
    total: z.number().int().min(0),
    limit: z.number().int().min(0),
    offset: z.number().int().min(0),
    has_more: z.boolean(),
  });

export const ValidationEventResponseSchema = z.looseObject({
    id: z.string(),
    from_status: z.string().nullable().optional(),
    to_status: z.string(),
    from_maturity: z.number().nullable().optional(),
    to_maturity: z.number(),
    actor: z.string().nullable().optional(),
    actor_type: z.string(),
    confidence_at_transition: z.number().nullable().optional(),
    source_count_at_transition: z.number().nullable().optional(),
    notes: z.string().nullable().optional(),
    created_at: z.string(),
  });

export const ValidationEventListResponseSchema = z.array(
  ValidationEventResponseSchema
);

export const FreshnessCountsSchema = z.looseObject({
    stale: z.number().int().min(0),
    fresh: z.number().int().min(0),
    expiring_soon: z.number().int().min(0),
    total: z.number().int().min(0),
  });

export const FreshnessSummaryResponseSchema = z.looseObject({
    tenant_id: z.string(),
    timestamp: z.string(),
    summary: FreshnessCountsSchema,
    warning_threshold_days: z.number().int().min(0),
  });

export const StaleTruthsEnvelopeSchema = z.looseObject({
    items: z.array(TruthObjectSummarySchema),
    total: z.number().int().min(0).optional(),
    limit: z.number().int().min(0).optional(),
    offset: z.number().int().min(0).optional(),
    has_more: z.boolean().optional(),
  });

export const MaturityLevelDetailSchema = z.looseObject({
    level: z.number(),
    name: z.string(),
    description: z.string(),
    required_status: z.string(),
    advancement_trigger: z.string(),
  });

export const MaturityLadderResponseSchema = z.looseObject({
    levels: z.array(MaturityLevelDetailSchema),
  });

export type TruthStatus = z.infer<typeof TruthStatusSchema>;
export type ClaimType = z.infer<typeof ClaimTypeSchema>;
export type TruthObjectSummary = z.infer<typeof TruthObjectSummarySchema>;
export type TruthObjectListResponse = z.infer<
  typeof TruthObjectListResponseSchema
>;
export type ValidationEventResponse = z.infer<
  typeof ValidationEventResponseSchema
>;
export type FreshnessSummaryResponse = z.infer<
  typeof FreshnessSummaryResponseSchema
>;
export type StaleTruthsResponse = TruthObjectListResponse;
export type MaturityLadderResponse = z.infer<typeof MaturityLadderResponseSchema>;

export function parseTruthObjectListResponse(
  data: unknown
): TruthObjectListResponse {
  return TruthObjectListResponseSchema.parse(unwrapGovernanceEnvelope(data));
}

export function parseValidationEventListResponse(
  data: unknown
): ValidationEventResponse[] {
  return ValidationEventListResponseSchema.parse(unwrapGovernanceEnvelope(data));
}

export function parseFreshnessSummaryResponse(
  data: unknown
): FreshnessSummaryResponse {
  return FreshnessSummaryResponseSchema.parse(unwrapGovernanceEnvelope(data));
}

export function parseStaleTruthsResponse(
  data: unknown,
  params: { limit?: number; offset?: number } = {}
): StaleTruthsResponse {
  const normalized = unwrapGovernanceEnvelope(data);
  const envelope = Array.isArray(normalized)
    ? { items: data }
    : StaleTruthsEnvelopeSchema.parse(normalized);

  const items = z.array(TruthObjectSummarySchema).parse(envelope.items);
  const passthroughFields =
    envelope && typeof envelope === "object" && !Array.isArray(envelope)
      ? (envelope as Record<string, unknown>)
      : {};

  return TruthObjectListResponseSchema.parse({
    ...passthroughFields,
    items,
    total:
      typeof passthroughFields.total === "number"
        ? passthroughFields.total
        : items.length,
    limit:
      typeof passthroughFields.limit === "number"
        ? passthroughFields.limit
        : (params.limit ?? items.length),
    offset:
      typeof passthroughFields.offset === "number"
        ? passthroughFields.offset
        : (params.offset ?? 0),
    has_more:
      typeof passthroughFields.has_more === "boolean"
        ? passthroughFields.has_more
        : false,
  });
}

export function parseMaturityLadderResponse(data: unknown): MaturityLadderResponse {
  return MaturityLadderResponseSchema.parse(unwrapGovernanceEnvelope(data));
}


export const GovernanceEnvelopeSchema = z.looseObject({
  content: z.unknown().optional(),
  claim_citations: z.array(z.object({ claim_id: z.string(), source_id: z.string() })).default([]),
  evidence_provenance_ids: z.array(z.string()).default([]),
  refusal_reason: z.string().nullable().optional(),
  policy_decision: z.enum(["allow", "allow_with_redaction", "needs_approval", "deny"]),
  tenant_scope: z.object({ tenant_id: z.string(), scope: z.enum(["tenant", "cross_tenant_blocked"]) }),
  approval_required: z.boolean(),
});

export function unwrapGovernanceEnvelope(data: unknown): unknown {
  const parsed = GovernanceEnvelopeSchema.safeParse(data);
  if (!parsed.success) return data;
  return parsed.data.content ?? data;
}
