/**
 * extraction.ts — Tier 1 Protocol Hooks for Layer 2 Extraction API
 *
 * Contract: Hook Architecture Contract §2.1
 * These functions contain ONLY HTTP mechanics + Zod validation.
 * No React Query, no domain logic, no error formatting.
 */
import { z } from 'zod';
import { apiClient, type LayerKey } from '@/api/client';

// ── Request / Response Schemas ───────────────────────────────────────────────

const ExtractionStatusResponseSchema = z.object({
  job_id: z.string(),
  overall_status: z.string(),
  extraction_status: z.string(),
  ingestion_status: z.string().optional(),
  entities_extracted: z.number(),
  relationships_extracted: z.number(),
  last_error: z.string().nullable(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
});

export const ExtractedEntitySchema = z.object({
  entity_id: z.string(),
  type: z.string(),
  name: z.string(),
  confidence: z.number().min(0).max(1),
  source_span: z.object({
    document_id: z.string(),
    start: z.number(),
    end: z.number(),
  }).optional(),
  provenance: z.object({
    extraction_job_id: z.string(),
    source_url: z.string().nullable(),
    trace_id: z.string().nullable(),
  }).optional(),
  attributes: z.record(z.string(), z.unknown()).optional().refine(
    (value) => value === undefined || Object.values(value).every((item) => item !== undefined),
    'attributes values must be defined when provided'
  ),
});

export const ExtractionResultsResponseSchema = z.object({
  summary: z.object({
    job_id: z.string(),
    total_entities: z.number(),
    returned_entities: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
    mode: z.enum(['summary', 'full']),
  }),
  entities: z.array(ExtractedEntitySchema),
});

// ── Types ────────────────────────────────────────────────────────────────────

export type ExtractionStatusResponse = z.infer<typeof ExtractionStatusResponseSchema>;
export type ExtractedEntity = z.infer<typeof ExtractedEntitySchema>;

// ── Tier 1 Fetchers ──────────────────────────────────────────────────────────

const LAYER: LayerKey = 'l2';

/**
 * Fetch extraction job status.
 * Tier 1: HTTP mechanics + Zod validation only.
 */
export async function fetchExtractionStatus(jobId: string): Promise<ExtractionStatusResponse> {
  const response = await apiClient.get(LAYER, `/v1/extract/status/${jobId}`);
  const parsed = ExtractionStatusResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new Error(`Invalid extraction status response: ${parsed.error.message}`);
  }
  return parsed.data;
}

/**
 * Fetch extracted entities for a job.
 * Tier 1: HTTP mechanics + Zod validation only.
 *
 * Backend endpoint implemented (ticket L2-42).
 * Calls GET /v1/extract/{job_id}/entities.
 */
export async function fetchExtractedEntities(jobId: string): Promise<ExtractedEntity[]> {
  const response = await apiClient.get(LAYER, `/v1/extract/results/${jobId}`);
  const parsed = ExtractionResultsResponseSchema.safeParse(response.data);
  if (!parsed.success) {
    throw new Error(`Invalid extracted entities response: ${parsed.error.message}`);
  }
  return parsed.data.entities;
}
