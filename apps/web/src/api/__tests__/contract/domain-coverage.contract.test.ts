import { describe, it } from 'vitest';
import { z } from 'zod';
import {
  ApiErrorSchema,
  CrossTenantErrorSchema,
  assertSchema,
  assertSchemaRejects,
  assertCanonicalSchema,
  OperationalSignalLifecycleRecordSchema,
  fixtures,
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
  it('matches OpenAPI operational signal lifecycle schema', () => {
    assertCanonicalSchema(
      OperationalSignalLifecycleRecordSchema,
      'layer2-extraction.json',
      '#/components/schemas/OperationalSignalLifecycleRecord',
      fixtures.operationalSignalLifecycleRecord(),
      'Data domain operational signal lifecycle'
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
