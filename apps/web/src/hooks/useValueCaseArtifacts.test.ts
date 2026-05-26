import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import { useValueCaseArtifacts, type ValueCaseArtifactsInput } from './useValueCaseArtifacts';

const mutateAsync = vi.fn();
vi.mock('./useNarratives', () => ({
  useGenerateNarrative: () => ({ mutateAsync }),
}));

const sampleInput: ValueCaseArtifactsInput = {
  account_id: 'acct-1',
  account_name: 'Acme',
  stakeholders: ['CFO'],
  accepted_evidence: ['e1'],
  scenario_assumptions: ['a1'],
  roi_metrics: { three_year_value: '$100', roi: '200%', payback: '12m' },
  risk_notes: ['risk-1'],
};

describe('useValueCaseArtifacts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mutateAsync.mockResolvedValue({
      id: 'n-1',
      title: 'Narrative 1',
      sections: [],
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

  it('generates and persists a new artifact (success path)', async () => {
    const { result } = renderHook(() => useValueCaseArtifacts('acct-1'), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.generateArtifact.mutateAsync(sampleInput);
    });

    await waitFor(() => expect(result.current.versions).toHaveLength(1));
    expect(result.current.selectedVersion?.id).toBe('acct-1-v1');
    expect(result.current.versions[0]?.business_case.summary).toContain('200% ROI');
  });

  it('surfaces mutation failure and keeps versions empty (error path)', async () => {
    mutateAsync.mockRejectedValueOnce(new Error('narrative failed'));
    const { result } = renderHook(() => useValueCaseArtifacts('acct-1'), { wrapper: createWrapper() });

    await act(async () => {
      await expect(result.current.generateArtifact.mutateAsync(sampleInput)).rejects.toThrow('narrative failed');
    });

    expect(result.current.versions).toEqual([]);
    await waitFor(() => expect(result.current.generateArtifact.isError).toBe(true));
  });
});
