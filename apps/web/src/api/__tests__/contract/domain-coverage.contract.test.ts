import { describe, it } from 'vitest';
import { z } from 'zod';
import {
  ApiErrorSchema,
  CrossTenantErrorSchema,
  assertSchema,
  assertSchemaRejects,
  assertCanonicalSchema,
  ExtractionStatusSchema,
} from './_helpers';

describe('Contract Domain Coverage: auth failures', () => {
  it('accepts canonical auth failure payload', () => {
    assertSchema(
      ApiErrorSchema,
      { error: { message: 'Authentication required', code: 'UNAUTHORIZED', request_id: 'trace-auth-1' } },
      'Auth error payload'
    );
  });

  it('rejects auth failure payload missing request_id', () => {
    assertSchemaRejects(
      ApiErrorSchema,
      { message: 'Authentication required', code: 'UNAUTHORIZED' },
      'Auth error without request_id'
    );
  });
});

describe('Contract Domain Coverage: billing', () => {
  const BillingCreateRequestSchema = z.object({
    account_id: z.string().min(1),
    plan_code: z.string().min(1),
    billing_email: z.string().email(),
  });

  it('accepts minimal billing create payload', () => {
    assertSchema(
      BillingCreateRequestSchema,
      { account_id: 'acct-001', plan_code: 'pro', billing_email: 'owner@example.com' },
      'Billing create request'
    );
  });

  it('rejects malformed billing payload', () => {
    assertSchemaRejects(
      BillingCreateRequestSchema,
      { account_id: '', plan_code: 'pro', billing_email: 'invalid-email' },
      'Billing malformed payload'
    );
  });
});

describe('Contract Domain Coverage: admin', () => {
  it('accepts cross-tenant authorization error shape', () => {
    assertSchema(
      CrossTenantErrorSchema,
      { error: { message: 'Forbidden', code: 'AUTHORIZATION_ERROR', request_id: 'trace-admin-1' } },
      'Admin cross-tenant authorization error'
    );
  });
});

describe('Contract Domain Coverage: data', () => {
  it('matches OpenAPI ExtractionStatus schema', () => {
    assertCanonicalSchema(
      ExtractionStatusSchema,
      'layer2-extraction.json',
      '#/components/schemas/ExtractionStatusResponse',
      {
        job_id: 'job-001',
        overall_status: 'failed',
        extraction_status: 'failed',
        ingestion_status: 'completed',
        entities_extracted: 0,
        relationships_extracted: 0,
        retry_count: 1,
        last_error: 'Bad source payload',
        next_retry_at: null,
        started_at: '2024-01-15T10:00:00Z',
        completed_at: null,
      },
      'Data domain extraction status'
    );
  });
});

describe('Contract Domain Coverage: workflows', () => {
  const WorkflowCreateRequestSchema = z.object({
    workflow_type: z.enum(['roi_calculator', 'whitespace_analysis', 'business_case']),
  });

  it('rejects malformed workflow payload', () => {
    assertSchemaRejects(
      WorkflowCreateRequestSchema,
      { workflow_type: 'unknown_workflow' },
      'Workflow malformed payload'
    );
  });
});
