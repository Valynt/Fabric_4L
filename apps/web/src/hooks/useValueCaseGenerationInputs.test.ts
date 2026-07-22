import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import { useValueCaseGenerationInputs } from './useValueCaseGenerationInputs';

vi.mock('@/features/intelligence-workspace/tabs/_shared/useWorkspaceData', () => ({
  useStakeholdersData: vi.fn(),
}));

vi.mock('@/hooks/useGroundTruthGovernance', () => ({
  useTruths: vi.fn(),
}));

vi.mock('@/hooks/useROICalculator', () => ({
  useROICalculations: vi.fn(),
}));

import { useStakeholdersData } from '@/features/intelligence-workspace/tabs/_shared/useWorkspaceData';
import { useTruths } from '@/hooks/useGroundTruthGovernance';
import { useROICalculations } from '@/hooks/useROICalculator';

function mockQuery(overrides: Partial<ReturnType<typeof useStakeholdersData>> = {}) {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    error: null,
    isSuccess: true,
    items: [],
    ...overrides,
  };
}

describe('useValueCaseGenerationInputs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useStakeholdersData as Mock).mockReturnValue(mockQuery({ items: [] }));
    (useTruths as Mock).mockReturnValue(mockQuery({ data: { items: [] } }));
    (useROICalculations as Mock).mockReturnValue(mockQuery({ data: { calculations: [] } }));
  });

  it('maps live sources into a ValueCaseArtifactsInput draft', async () => {
    (useStakeholdersData as Mock).mockReturnValue(mockQuery({
      items: [{ id: 'st-1', name: 'CFO', role: 'Economic Buyer' }],
    }));
    (useTruths as Mock).mockReturnValue(mockQuery({
      data: { items: [{ id: 'truth-1', claim: 'Validated efficiency gap' }] },
    }));
    (useROICalculations as Mock).mockReturnValue(mockQuery({
      data: {
        calculations: [{
          id: 'roi-1',
          npv: 1_800_000,
          total_roi_pct: 214,
          payback_months: 9,
        }],
      },
    }));

    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs('acct-1', 'Acme', 'case-1'),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    expect(result.current.draft.account_id).toBe('acct-1');
    expect(result.current.draft.account_name).toBe('Acme');
    expect(result.current.draft.stakeholders).toEqual(['CFO']);
    expect(result.current.draft.accepted_evidence).toEqual(['Validated efficiency gap']);
    expect(result.current.draft.scenario_assumptions).toEqual([]);
    expect(result.current.draft.roi_metrics).toEqual({
      three_year_value: '$1.8M',
      roi: '214%',
      payback: '9 months',
    });
    expect(result.current.provenance.stakeholders).toEqual([{ source: 'workspace_stakeholder', id: 'st-1' }]);
  });

  it('never returns the legacy hardcoded values', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(
      () => useValueCaseGenerationInputs('acct-1', 'Acme', 'case-1'),
      { wrapper }
    );

    await waitFor(() => expect(result.current.isReady).toBe(true));

    const json = JSON.stringify(result.current.draft);
    expect(json).not.toContain('Economic buyer');
    expect(json).not.toContain('Business champion');
    expect(json).not.toContain('$1.8M');
    expect(json).not.toContain('214%');
    expect(json).not.toContain('9 months');
  });
});
