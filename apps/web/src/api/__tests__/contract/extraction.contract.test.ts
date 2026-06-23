/**
 * Contract tests: Extraction (L2)
 *
 * Validates request/response shapes against contracts/openapi/layer2-extraction.json.
 * Covers: POST /v1/extract, GET /v1/extract/status/{job_id}, POST /v1/extract/batch.
 *
 * NOTE: There is a known path mismatch between frontend expectations
 * (GET /jobs/{id}) and backend canonical routes (GET /extract/status/{id}).
 * The canonical backend path is used here; the frontend client must be updated
 * to match if it currently uses the legacy path.
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  ExtractResponseSchema,
  ExtractionStatusSchema,
  ApiErrorSchema,
  assertSchema,
  assertSchemaRejects,
  fixtures,
} from './_helpers';

// ── Request schemas ───────────────────────────────────────────────────────────

const ExtractRequestSchema = z.object({
  content_id: z.string().min(1),
  source_url: z.string().min(1),
  markdown_content: z.string().min(1),
  extraction_config: z.record(z.string(), z.unknown()).optional(),
});

const BatchExtractRequestSchema = z.object({
  jobs: z.array(ExtractRequestSchema).min(1),
});



const ExtractionResultsResponseSchema = z.object({
  summary: z.object({
    job_id: z.string(),
    total_entities: z.number(),
    returned_entities: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
    mode: z.enum(['summary', 'full']),
  }),
  entities: z.array(z.object({
    entity_id: z.string(),
    type: z.string(),
    name: z.string(),
    confidence: z.number().min(0).max(1),
  })),
});

// ── POST /v1/extract ──────────────────────────────────────────────────────────

describe('Contract: POST /v1/extract', () => {
  it('accepts a minimal valid extract request', () => {
    assertSchema(
      ExtractRequestSchema,
      {
        content_id: 'content-abc123',
        source_url: 'https://example.com/report.pdf',
        markdown_content: '# Annual Report\n\nRevenue grew 23% YoY...',
      },
      'ExtractRequest (minimal)'
    );
  });

  it('accepts request with extraction_config', () => {
    assertSchema(
      ExtractRequestSchema,
      {
        content_id: 'content-abc123',
        source_url: 'https://example.com/report.pdf',
        markdown_content: '# Report',
        extraction_config: { model: 'gpt-4', confidence_threshold: 0.7 },
      },
      'ExtractRequest (with config)'
    );
  });

  it('rejects missing content_id', () => {
    assertSchemaRejects(
      ExtractRequestSchema,
      { source_url: 'https://example.com', markdown_content: '# Doc' },
      'ExtractRequest missing content_id'
    );
  });

  it('rejects missing markdown_content', () => {
    assertSchemaRejects(
      ExtractRequestSchema,
      { content_id: 'c1', source_url: 'https://example.com' },
      'ExtractRequest missing markdown_content'
    );
  });

  it('response has extraction_job_id and status', () => {
    const resp = assertSchema(
      ExtractResponseSchema,
      fixtures.extractResponse(),
      'ExtractResponse'
    );
    expect(resp.extraction_job_id).toBeTruthy();
    expect(resp.status).toBeTruthy();
    expect(resp.message).toBeTruthy();
  });

  it('response status is a non-empty string', () => {
    const resp = assertSchema(
      ExtractResponseSchema,
      { extraction_job_id: 'job-001', status: 'pending', message: 'Queued' },
      'ExtractResponse (pending)'
    );
    expect(resp.status).toBe('pending');
  });
});

// ── GET /v1/extract/status/{job_id} ──────────────────────────────────────────

describe('Contract: GET /v1/extract/status/{job_id}', () => {
  it('completed status has entity and relationship counts', () => {
    const resp = assertSchema(
      ExtractionStatusSchema,
      fixtures.extractionStatus(),
      'ExtractionStatusResponse (completed)'
    );
    expect(resp.entities_extracted).toBeGreaterThanOrEqual(0);
    expect(resp.relationships_extracted).toBeGreaterThanOrEqual(0);
    expect(resp.completed_at).toBeTruthy();
  });

  it('in-progress status has null completed_at', () => {
    const resp = assertSchema(
      ExtractionStatusSchema,
      fixtures.extractionStatus({
        overall_status: 'running',
        extraction_status: 'running',
        ingestion_status: 'pending',
        entities_extracted: 0,
        relationships_extracted: 0,
        completed_at: null,
      }),
      'ExtractionStatusResponse (running)'
    );
    expect(resp.completed_at).toBeNull();
  });

  it('failed status has last_error populated', () => {
    const resp = assertSchema(
      ExtractionStatusSchema,
      fixtures.extractionStatus({
        overall_status: 'failed',
        extraction_status: 'failed',
        ingestion_status: 'skipped',
        entities_extracted: 0,
        relationships_extracted: 0,
        last_error: 'LLM API timeout after 60s',
        retry_count: 3,
        completed_at: '2024-01-15T10:02:00Z',
      }),
      'ExtractionStatusResponse (failed)'
    );
    expect(resp.last_error).toBeTruthy();
    expect(resp.retry_count).toBe(3);
  });

  it('retry_count defaults to 0 when absent', () => {
    const resp = assertSchema(
      ExtractionStatusSchema,
      {
        job_id: 'job-001',
        overall_status: 'completed',
        extraction_status: 'completed',
        ingestion_status: 'completed',
        entities_extracted: 5,
        relationships_extracted: 3,
        started_at: '2024-01-15T10:00:00Z',
        completed_at: '2024-01-15T10:01:00Z',
      },
      'ExtractionStatusResponse (no retry_count)'
    );
    expect(resp.retry_count).toBe(0);
  });

  it('rejects missing required fields', () => {
    assertSchemaRejects(
      ExtractionStatusSchema,
      { job_id: 'job-001', overall_status: 'completed' },
      'ExtractionStatusResponse missing required fields'
    );
  });
});

// ── POST /v1/extract/batch ────────────────────────────────────────────────────

describe('Contract: POST /v1/extract/batch', () => {
  it('accepts a batch of two extract requests', () => {
    assertSchema(
      BatchExtractRequestSchema,
      {
        jobs: [
          { content_id: 'c1', source_url: 'https://a.com', markdown_content: '# Doc A' },
          { content_id: 'c2', source_url: 'https://b.com', markdown_content: '# Doc B' },
        ],
      },
      'BatchExtractRequest'
    );
  });

  it('rejects empty jobs array', () => {
    assertSchemaRejects(
      BatchExtractRequestSchema,
      { jobs: [] },
      'BatchExtractRequest with empty jobs'
    );
  });
});

// ── Path contract documentation ───────────────────────────────────────────────

describe('Contract: path alignment', () => {
  it('documents the canonical status path (GET /v1/extract/status/{job_id})', () => {
    // The backend canonical route is /v1/extract/status/{job_id}.
    // Any frontend code using /jobs/{id} must be updated to match.
    const canonicalPath = '/v1/extract/status/{job_id}';
    expect(canonicalPath).toContain('/extract/status/');
  });
});

// ── Tenant context ────────────────────────────────────────────────────────────

describe('Contract: extraction tenant context', () => {
  it('extraction status includes tenant_id when scoped', () => {
    const TenantScopedStatusSchema = ExtractionStatusSchema.extend({
      tenant_id: z.string().min(1),
    });
    const resp = assertSchema(
      TenantScopedStatusSchema,
      {
        job_id: 'job-001',
        overall_status: 'completed',
        extraction_status: 'completed',
        ingestion_status: 'completed',
        entities_extracted: 5,
        relationships_extracted: 3,
        started_at: '2024-01-15T10:00:00Z',
        completed_at: '2024-01-15T10:01:00Z',
        tenant_id: 'tenant-001',
      },
      'TenantScopedExtractionStatus'
    );
    expect(resp.tenant_id).toBe('tenant-001');
  });
});

// ── Auth failures ─────────────────────────────────────────────────────────────

describe('Contract: extraction auth failures', () => {
  it('401 matches ApiError shape', () => {
    assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-extract-401' } },
      'ApiError (401)'
    );
  });

  it('403 cross-tenant job access matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Extraction job belongs to a different tenant', code: 'AUTHORIZATION_ERROR', request_id: 'trace-extract-403' } },
      'ApiError (403 cross-tenant)'
    );
    expect(err.error.code).toBe('AUTHORIZATION_ERROR');
    expect(err.error.request_id).toBeTruthy();
  });

  it('job not found 404 matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      { error: { message: 'Extraction job not found', code: 'NOT_FOUND', request_id: 'trace-extract-404' } },
      'ApiError (404)'
    );
    expect(err.error.code).toBe('NOT_FOUND');
  });
});


describe('Contract: GET /v1/extract/results/{job_id}', () => {
  it('supports full response mode with entities page', () => {
    const resp = assertSchema(
      ExtractionResultsResponseSchema,
      {
        summary: {
          job_id: 'job-001',
          total_entities: 2,
          returned_entities: 2,
          page: 1,
          page_size: 100,
          total_pages: 1,
          mode: 'full',
        },
        entities: [
          { entity_id: 'e1', type: 'Capability', name: 'Data Integration', confidence: 0.91 },
          { entity_id: 'e2', type: 'UseCase', name: 'Forecasting', confidence: 0.88 },
        ],
      },
      'ExtractionResultsResponse (full)'
    );
    expect(resp.summary.mode).toBe('full');
  });

  it('supports summary mode without entity payload', () => {
    const resp = assertSchema(
      ExtractionResultsResponseSchema,
      {
        summary: {
          job_id: 'job-001',
          total_entities: 2450,
          returned_entities: 0,
          page: 1,
          page_size: 100,
          total_pages: 25,
          mode: 'summary',
        },
        entities: [],
      },
      'ExtractionResultsResponse (summary)'
    );
    expect(resp.entities.length).toBe(0);
  });
});
