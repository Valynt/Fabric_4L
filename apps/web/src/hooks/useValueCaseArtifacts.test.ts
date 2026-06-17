import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import React, { type ReactNode } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { createWrapper, createTestQueryClient } from '@/test-utils';
import { server } from '@/test/mocks/server';
import { QK } from './queryKeys';
import { useValueCaseArtifacts, type ValueCaseArtifactsInput } from './useValueCaseArtifacts';

const mutateAsync = vi.fn();
vi.mock('./useNarratives', () => ({
  useGenerateNarrative: () => ({ mutateAsync }),
}));

const accountId = 'acc-123';

const sampleInput: ValueCaseArtifactsInput = {
  account_id: accountId,
  account_name: 'Acme',
  stakeholders: ['CFO'],
  accepted_evidence: ['e1'],
  scenario_assumptions: ['a1'],
  roi_metrics: { three_year_value: '$100', roi: '200%', payback: '12m' },
  risk_notes: ['risk-1'],
};

function createApiCase(overrides: Record<string, unknown> = {}) {
  return {
    id: 'vc-1',
    account_id: accountId,
    title: 'Value Case — Acme',
    status: 'draft',
    audit: {
      created_at: '2026-01-01T00:00:00.000Z',
      updated_at: '2026-01-02T00:00:00.000Z',
    },
    executive_summary: '',
    value_case: {
      inputs: sampleInput,
      selected_scenario_id: null,
      sections: [],
      assumption_ids: [],
      evidence_ids: [],
      stakeholder_framing: [{ persona: 'CFO' }],
      claim_ids: [],
      roi_snapshot: null,
    },
    assumptions: [],
    risks: sampleInput.risk_notes,
    ...overrides,
  };
}

describe('useValueCaseArtifacts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mutateAsync.mockResolvedValue({
      id: 'n-1',
      title: 'Value case narrative — Acme',
      sections: [
        {
          section_type: 'executive_summary',
          title: 'Executive Summary',
          summary: 'Projected strong ROI based on accepted evidence.',
          detail: {},
          data_source: '',
          caller_supplied: false,
          verified: false,
        },
      ],
      created_at: '2026-01-01T00:00:00.000Z',
      updated_at: '2026-01-01T00:00:00.000Z',
    });
  });

  it('returns empty/default state when no account is provided', async () => {
    const { result } = renderHook(() => useValueCaseArtifacts(null), { wrapper: createWrapper() });
    expect(result.current.versions).toEqual([]);
    expect(result.current.selectedVersion).toBeNull();
    expect(result.current.isLoadingVersions).toBe(false);
  });

  it('loads versions from the backend', async () => {
    const apiCase = createApiCase({ id: 'vc-loaded' });
    server.use(
      http.get(`/api/v1/accounts/${accountId}/value-cases`, () =>
        HttpResponse.json([apiCase])
      )
    );

    const { result } = renderHook(() => useValueCaseArtifacts(accountId), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoadingVersions).toBe(false));

    expect(result.current.versions).toHaveLength(1);
    expect(result.current.versions[0]?.id).toBe('vc-loaded');
    expect(result.current.selectedVersion?.id).toBe('vc-loaded');
  });

  it('does not write durable data to localStorage', async () => {
    const setItemSpy = vi.spyOn(window.localStorage, 'setItem');
    const apiCase = createApiCase({ id: 'vc-local' });
    server.use(
      http.get(`/api/v1/accounts/${accountId}/value-cases`, () =>
        HttpResponse.json([apiCase])
      )
    );

    renderHook(() => useValueCaseArtifacts(accountId), { wrapper: createWrapper() });

    await waitFor(() => expect(setItemSpy).not.toHaveBeenCalled());
    setItemSpy.mockRestore();
  });

  it('generates and persists a value case to the backend and invalidates the query', async () => {
    let cases: unknown[] = [];
    let capturedBody: unknown = null;

    server.use(
      http.get(`/api/v1/accounts/${accountId}/value-cases`, () =>
        HttpResponse.json(cases)
      ),
      http.post(`/api/v1/accounts/${accountId}/value-case`, async ({ request }) => {
        capturedBody = await request.json();
        const created = createApiCase({ id: 'vc-new' });
        cases = [created];
        return HttpResponse.json(created, { status: 201 });
      })
    );

    const { result } = renderHook(() => useValueCaseArtifacts(accountId), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isLoadingVersions).toBe(false));
    expect(result.current.versions).toHaveLength(0);

    await act(async () => {
      await result.current.generateArtifact.mutateAsync(sampleInput);
    });

    expect(capturedBody).toMatchObject({
      title: 'Value Case — Acme',
      value_case: {
        inputs: sampleInput,
        sections: [
          expect.objectContaining({
            type: 'executive_summary',
            title: 'Executive Summary',
            content: 'Projected strong ROI based on accepted evidence.',
          }),
        ],
      },
    });

    await waitFor(() => expect(result.current.versions).toHaveLength(1));
    expect(result.current.versions[0]?.id).toBe('vc-new');
    expect(result.current.selectedVersion?.id).toBe('vc-new');
  });

  it('refresh rehydrates from the backend', async () => {
    let cases: unknown[] = [];
    const queryClient = createTestQueryClient();
    const wrapper = ({ children }: { children: ReactNode }) =>
      React.createElement(
        MemoryRouter,
        {},
        React.createElement(QueryClientProvider, { client: queryClient }, children)
      );

    server.use(
      http.get(`/api/v1/accounts/${accountId}/value-cases`, () =>
        HttpResponse.json(cases)
      )
    );

    const { result } = renderHook(() => useValueCaseArtifacts(accountId), { wrapper });

    await waitFor(() => expect(result.current.isLoadingVersions).toBe(false));
    expect(result.current.versions).toHaveLength(0);

    cases = [createApiCase({ id: 'vc-refreshed' })];

    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: QK.valueCases.account(accountId) });
    });

    await waitFor(() => expect(result.current.versions).toHaveLength(1));
    expect(result.current.versions[0]?.id).toBe('vc-refreshed');
  });
});
