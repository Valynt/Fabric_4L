import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import { buildCreateAccountPayload, createAccountPayloadSchema } from '@/hooks/useAccounts';
import { buildProspectSetupCreateAccountPayload } from '@/hooks/useProspectSetupAccount';
import { ApiErrorSchema, assertCanonicalSchema, assertSchema } from './_helpers';

const backendCreateAccountRequestSchema = z.object({
  id: z.string().uuid().optional(),
  provider: z.enum(['salesforce', 'hubspot', 'manual']),
  provider_record_id: z.string().min(1).max(100).optional(),
  name: z.string().min(1).max(255),
  domain: z.string().max(255).optional(),
  industry: z.string().max(100).optional(),
  region: z.string().max(100).optional(),
  company_size: z.number().int().min(0).optional(),
  annual_revenue: z.number().min(0).optional(),
  headquarters: z.string().max(255).optional(),
  website: z.string().max(255).optional(),
  owner_id: z.string().max(100).optional(),
  owner_name: z.string().max(255).optional(),
  owner_email: z.string().max(255).optional(),
  stage: z.string().max(50).optional(),
  segment: z.string().max(100).optional(),
});

describe('Contract: POST /accounts create payload', () => {
  it('matches canonical frontend snapshot payload shape', () => {
    const payload = buildCreateAccountPayload({
      provider: 'manual',
      provider_record_id: 'manual-acme-corp',
      name: 'Acme Corp',
      domain: 'acme.example',
      industry: 'Manufacturing',
      region: 'NA',
      company_size: 500,
      annual_revenue: 125000000,
      headquarters: 'Austin, TX',
      website: 'https://acme.example',
      owner_id: 'owner-001',
      owner_name: 'Casey Owner',
      owner_email: 'casey@acme.example',
      stage: 'prospect',
      segment: 'enterprise',
    });

    expect(payload).toMatchInlineSnapshot(`
      {
        "annual_revenue": 125000000,
        "company_size": 500,
        "domain": "acme.example",
        "headquarters": "Austin, TX",
        "industry": "Manufacturing",
        "name": "Acme Corp",
        "owner_email": "casey@acme.example",
        "owner_id": "owner-001",
        "owner_name": "Casey Owner",
        "provider": "manual",
        "provider_record_id": "manual-acme-corp",
        "region": "NA",
        "segment": "enterprise",
        "stage": "prospect",
        "website": "https://acme.example",
      }
    `);
  });

  it('frontend payload schema validates against backend request contract', () => {
    const payload = buildCreateAccountPayload({
      provider: 'manual',
      provider_record_id: 'manual-bravo-industries',
      name: 'Bravo Industries',
      stage: 'prospect',
    });

    expect(() => createAccountPayloadSchema.parse(payload)).not.toThrow();
    expect(() =>
      assertCanonicalSchema(
        backendCreateAccountRequestSchema,
        'layer4-agents.json',
        '#/components/schemas/CreateAccountRequest',
        payload,
        'CreateAccountRequest'
      )
    ).not.toThrow();
  });

  it('prospect setup entrypoints build the canonical account create payload', () => {
    const payload = buildProspectSetupCreateAccountPayload({
      companyName: 'Created Account Inc',
      companyDomain: 'https://www.created-account.example/path',
      industry: 'Manufacturing',
      buyingContext: '',
      whyNow: '',
      knownInitiative: '',
      stakeholders: {},
      businessPain: [],
      currentFriction: [],
      desiredOutcomes: [],
      desiredOutputs: [],
      outputType: 'account_brief',
      mode: 'Balanced',
      enrichmentDepth: 'standard',
      useUploadedFiles: false,
      usePriorAccountContext: false,
      runWebEnrichment: true,
      complianceSensitive: false,
      sourceArtifacts: [],
      freeformPrompt: 'Company: Created Account Inc',
    });

    expect(payload).toMatchObject({
      provider: 'manual',
      provider_record_id: 'manual-created-account-example',
      name: 'Created Account Inc',
      domain: 'created-account.example',
      website: 'created-account.example',
      industry: 'Manufacturing',
      stage: 'prospect',
    });
    expect(() =>
      assertCanonicalSchema(
        backendCreateAccountRequestSchema,
        'layer4-agents.json',
        '#/components/schemas/CreateAccountRequest',
        payload,
        'CreateAccountRequest'
      )
    ).not.toThrow();
  });
});

describe('Contract: accounts create auth failures', () => {
  it('401 unauthenticated account creation matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      {
        error: {
          message: 'Authentication required',
          code: 'AUTHENTICATION_ERROR',
          request_id: 'trace-account-create-401',
        },
      },
      'ApiError (401 account create)'
    );

    expect(err.error.code).toBe('AUTHENTICATION_ERROR');
    expect(err.error.request_id).toBeTruthy();
  });

  it('403 cross-tenant account creation matches ApiError shape', () => {
    const err = assertSchema(
      ApiErrorSchema,
      {
        error: {
          message: 'Tenant is not authorized to create this account',
          code: 'AUTHORIZATION_ERROR',
          request_id: 'trace-account-create-403',
        },
      },
      'ApiError (403 account create)'
    );

    expect(err.error.code).toBe('AUTHORIZATION_ERROR');
  });
});
