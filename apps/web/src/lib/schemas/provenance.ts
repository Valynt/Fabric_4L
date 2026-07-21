import { z } from "zod";

export const ProvenanceStepSchema = z.object({
  step: z.number(),
  label: z.string(),
  detail: z.string(),
  timestamp: z.string(),
  agent: z.string().optional(),
  entity_id: z.string().optional(),
});

export const ProvenanceTrailSchema = z.object({
  entity_id: z.string(),
  entity_type: z.string(),
  entity_name: z.string(),
  created_at: z.string(),
  source: z.string(),
  extraction_job_id: z.string().optional(),
  steps: z.array(ProvenanceStepSchema),
  confidence_score: z.number().optional(),
});

export const AuditLogEntrySchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  source: z.enum(["provenance", "access_log"]),
  event_type: z.string(),
  entity_id: z.string().optional(),
  entity_type: z.string().optional(),
  action: z.string(),
  agent: z.string(),
  details: z.record(z.string(), z.unknown()),
});

export const AuditLogResponseSchema = z.object({
  entries: z.array(AuditLogEntrySchema),
  total: z.number(),
  page: z.number(),
  per_page: z.number(),
});

export type ProvenanceStep = z.infer<typeof ProvenanceStepSchema>;
export type ProvenanceTrail = z.infer<typeof ProvenanceTrailSchema>;
export type AuditLogEntry = z.infer<typeof AuditLogEntrySchema>;
export type AuditLogResponse = z.infer<typeof AuditLogResponseSchema>;

function unwrapProvenanceEnvelope(data: unknown): unknown {
  const parsed = AgentResponseEnvelopeSchema.safeParse(data);
  if (!parsed.success) return data;
  return parsed.data.content ?? data;
}

export function parseProvenanceTrail(data: unknown): ProvenanceTrail {
  return ProvenanceTrailSchema.parse(unwrapProvenanceEnvelope(data));
}

export function parseAuditLogResponse(data: unknown): AuditLogResponse {
  return AuditLogResponseSchema.parse(unwrapProvenanceEnvelope(data));
}


export const ClaimCitationSchema = z.object({
  claim_id: z.string(),
  source_id: z.string(),
  quote: z.string().optional(),
  confidence: z.number().min(0).max(1).optional(),
});

export const TenantScopeSchema = z.object({
  tenant_id: z.string(),
  scope: z.enum(["tenant", "cross_tenant_blocked"]),
});

export const AgentResponseEnvelopeSchema = z.looseObject({
  content: z.string().nullable().optional(),
  claim_citations: z.array(ClaimCitationSchema).default([]),
  evidence_provenance_ids: z.array(z.string()).default([]),
  refusal_reason: z.string().nullable().optional(),
  policy_decision: z.enum(["allow", "allow_with_redaction", "needs_approval", "deny"]),
  tenant_scope: TenantScopeSchema,
  approval_required: z.boolean(),
});

export type ClaimCitation = z.infer<typeof ClaimCitationSchema>;
export type TenantScope = z.infer<typeof TenantScopeSchema>;
export type AgentResponseEnvelope = z.infer<typeof AgentResponseEnvelopeSchema>;

export function parseAgentResponseEnvelope(data: unknown): AgentResponseEnvelope {
  return AgentResponseEnvelopeSchema.parse(data);
}
