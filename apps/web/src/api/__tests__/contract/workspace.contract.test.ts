/**
 * Contract tests: Workspace Tab API
 *
 * The checked-in OpenAPI contract for these endpoints is intentionally sparse,
 * so these tests codify the frontend/backend contract with shared Zod schemas
 * and canonical fixtures. They specifically prevent the prior regression where
 * dynamic workspace tab payloads were accepted by mocks but stripped or reshaped
 * by the backend response model.
 */

import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import {
  ApiErrorSchema,
  WorkspaceActionPlanItemSchema,
  WorkspaceDriverSchema,
  WorkspaceEvidenceSchema,
  WorkspaceGenerateResponseSchema,
  WorkspaceNarrativeItemSchema,
  WorkspaceSignalSchema,
  WorkspaceStakeholderSchema,
  WorkspaceTabKeySchema,
  WorkspaceValueModelItemSchema,
  WorkspaceTabResponseSchema,
  WorkspaceUpdateResponseSchema,
  assertSchema,
  assertSchemaRejects,
  fixtures,
} from './_helpers';

const tenantScopedHeadersSchema = z.object({
  authorization: z.string().regex(/^Bearer\s+\S+$/),
  'x-tenant-id': z.string().uuid(),
});

const workspaceTabPayloadCases = [
  {
    tab: 'signals',
    itemSchema: WorkspaceSignalSchema,
    response: { signals: [fixtures.workspaceSignal()] },
  },
  {
    tab: 'drivers',
    itemSchema: WorkspaceDriverSchema,
    response: { drivers: [fixtures.workspaceDriver()] },
  },
  {
    tab: 'evidence',
    itemSchema: WorkspaceEvidenceSchema,
    response: { evidence: [fixtures.workspaceEvidence()] },
  },
  {
    tab: 'stakeholders',
    itemSchema: WorkspaceStakeholderSchema,
    response: { stakeholders: [fixtures.workspaceStakeholder()] },
  },
  {
    tab: 'action-plan',
    itemSchema: WorkspaceActionPlanItemSchema,
    response: { 'action-plan': [fixtures.workspaceActionPlanItem()] },
  },
  {
    tab: 'value-model',
    itemSchema: WorkspaceValueModelItemSchema,
    response: { 'value-model': [fixtures.workspaceValueModelItem()] },
  },
  {
    tab: 'narrative',
    itemSchema: WorkspaceNarrativeItemSchema,
    response: { narrative: [fixtures.workspaceNarrativeItem()] },
  },
] as const;

describe('Contract: Workspace Tab API', () => {
  describe('GET /v1/cases/{case_id}/workspace/{tab_key}', () => {
    it.each(workspaceTabPayloadCases.map((contract) => [contract.tab, contract] as const))(
      'validates the %s tab response with its schema-backed payload',
      (_label, { tab, itemSchema, response }) => {
        const parsed = assertSchema(
          WorkspaceTabResponseSchema,
          response,
          `GET workspace ${tab} response`
        );
        const payload = parsed[tab];

        expect(Array.isArray(payload)).toBe(true);
        expect(payload).toHaveLength(1);
        assertSchema(itemSchema, payload?.[0], `GET workspace ${tab} item`);
      }
    );

    it('preserves dynamic tab keys instead of accepting stripped empty responses', () => {
      assertSchema(
        WorkspaceTabResponseSchema,
        { signals: [fixtures.workspaceSignal()] },
        'dynamic workspace tab response'
      );

      assertSchemaRejects(
        WorkspaceTabResponseSchema,
        {},
        'stripped workspace tab response'
      );
    });

    it('rejects payloads that contain multiple workspace tabs in one response', () => {
      assertSchemaRejects(
        WorkspaceTabResponseSchema,
        {
          signals: [fixtures.workspaceSignal()],
          drivers: [fixtures.workspaceDriver()],
        },
        'multi-tab workspace response'
      );
    });

    it('validates empty arrays for known cases with no data while preserving the tab key', () => {
      const parsed = assertSchema(
        WorkspaceTabResponseSchema,
        { signals: [] },
        'empty workspace signals response'
      );

      expect(parsed.signals).toEqual([]);
    });

    it('rejects invalid tab keys before a request is sent', () => {
      expect(WorkspaceTabKeySchema.options).toEqual([
        'signals',
        'drivers',
        'evidence',
        'stakeholders',
        'action-plan',
        'value-model',
        'narrative',
      ]);
      assertSchemaRejects(WorkspaceTabKeySchema, 'invalid', 'invalid workspace tab key');
      assertSchemaRejects(WorkspaceTabKeySchema, '', 'empty workspace tab key');
    });

    it('validates tenant-scoped authenticated request metadata', () => {
      const parsed = assertSchema(
        tenantScopedHeadersSchema,
        {
          authorization: 'Bearer eyJhbGciOiJIUzI1NiJ9.test.signature',
          'x-tenant-id': '550e8400-e29b-41d4-a716-446655440000',
        },
        'workspace tenant-scoped headers'
      );

      expect(parsed['x-tenant-id']).toBe('550e8400-e29b-41d4-a716-446655440000');
      assertSchemaRejects(
        tenantScopedHeadersSchema,
        { authorization: 'Bearer token' },
        'workspace request without tenant context'
      );
    });

    it('validates auth and invalid-tab error response shapes', () => {
      assertSchema(
        ApiErrorSchema,
        {
          error: {
            message: 'Authentication required',
            code: 'AUTHENTICATION_ERROR',
            request_id: 'trace-workspace-401',
          },
        },
        'workspace auth failure response'
      );

      assertSchema(
        ApiErrorSchema,
        {
          error: {
            message: 'Invalid tab_key. Must be one of the allowed workspace tabs.',
            code: 'VALIDATION_ERROR',
            request_id: 'trace-workspace-400',
          },
        },
        'workspace invalid-tab error response'
      );
    });
  });

  describe('PUT /v1/cases/{case_id}/workspace/{tab_key}', () => {
    it.each(workspaceTabPayloadCases.map((contract) => [contract.tab, contract] as const))(
      'validates the %s update request body against the same tab payload contract',
      (_label, { tab, response }) => {
        assertSchema(
          WorkspaceTabResponseSchema,
          response,
          `PUT workspace ${tab} request body`
        );
      }
    );

    it('validates the update acknowledgement response', () => {
      const parsed = assertSchema(
        WorkspaceUpdateResponseSchema,
        {
          case_id: 'case-123',
          tab: 'signals',
          updated: true,
        },
        'workspace update response'
      );

      expect(parsed.updated).toBe(true);
    });
  });

  describe('GET /v1/cases/{case_id}/workspace/{tab_key} — pagination', () => {
    it('paginated workspace tab items have required pagination fields', () => {
      const PaginatedWorkspaceTabSchema = z.object({
        items: z.array(WorkspaceSignalSchema),
        total: z.number().int().nonnegative(),
        page: z.number().int().positive(),
        page_size: z.number().int().positive(),
        has_more: z.boolean(),
      });

      const resp = assertSchema(
        PaginatedWorkspaceTabSchema,
        { items: [], total: 0, page: 1, page_size: 20, has_more: false },
        'PaginatedWorkspaceSignals (empty)'
      );
      expect(resp.has_more).toBe(false);
    });
  });

  describe('Contract: workspace auth failures', () => {
    it('401 matches ApiError shape', () => {
      assertSchema(
        ApiErrorSchema,
        { error: { message: 'Authentication required', code: 'AUTHENTICATION_ERROR', request_id: 'trace-ws-401' } },
        'ApiError (401 workspace)'
      );
    });

    it('403 cross-tenant workspace access matches ApiError shape', () => {
      const err = assertSchema(
        ApiErrorSchema,
        { error: { message: 'Case does not belong to your tenant', code: 'AUTHORIZATION_ERROR', request_id: 'trace-ws-403' } },
        'ApiError (403 workspace)'
      );
      expect(err.error.code).toBe('AUTHORIZATION_ERROR');
      expect(err.error.request_id).toBeTruthy();
    });

    it('404 case not found matches ApiError shape', () => {
      const err = assertSchema(
        ApiErrorSchema,
        { error: { message: 'Case not found', code: 'NOT_FOUND', request_id: 'trace-ws-404' } },
        'ApiError (404 workspace)'
      );
      expect(err.error.code).toBe('NOT_FOUND');
    });
  });

  describe('POST /v1/cases/{case_id}/workspace/generate', () => {
    it('validates the production generation response shape when generation is implemented', () => {
      const parsed = assertSchema(
        WorkspaceGenerateResponseSchema,
        {
          case_id: 'case-123',
          account_id: '550e8400-e29b-41d4-a716-446655440000',
          generated: true,
          stats: {
            signals: 3,
            drivers: 3,
            evidence: 2,
            stakeholders: 3,
          },
        },
        'workspace generation response'
      );

      expect(parsed.stats.signals + parsed.stats.drivers).toBeGreaterThan(0);
    });

    it('rejects sample-like generation responses that omit required tenant/account context', () => {
      assertSchemaRejects(
        WorkspaceGenerateResponseSchema,
        {
          case_id: 'case-123',
          generated: true,
          stats: { signals: 3, drivers: 3, evidence: 2, stakeholders: 3 },
        },
        'workspace generation response without account context'
      );
    });

    it('validates explicit fail-closed not-implemented errors without accepting fabricated sample data', () => {
      assertSchema(
        ApiErrorSchema,
        {
          error: {
            message: 'Workspace intelligence generation requires the production AI workflow integration and will not return sample data.',
            code: 'not_implemented',
            request_id: 'trace-workspace-501',
          },
        },
        'workspace generation fail-closed response'
      );
    });
  });
});
