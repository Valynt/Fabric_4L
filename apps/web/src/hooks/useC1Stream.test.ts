/**
 * useC1Stream Hook Tests
 *
 * Behavior coverage for the streaming hook's callbacks. The key invariant:
 * callbacks that read `businessCaseData` must always see the latest value,
 * not the value captured when the hook first rendered.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { evaluateWhatIf, type WhatIfResult } from '@/api/thesysClient';
import { useC1Stream } from './useC1Stream';

vi.mock('@/api/thesysClient', () => ({
  streamC1Response: vi.fn(),
  evaluateWhatIf: vi.fn(),
  saveScenario: vi.fn(() => 'scenario-id'),
  getScenarios: vi.fn(() => []),
  isC1Enabled: vi.fn(() => true),
}));

const evaluateWhatIfMock = vi.mocked(evaluateWhatIf);

const whatIfResult: WhatIfResult = {
  original_value: 100,
  adjusted_value: 150,
  delta_percentage: 50,
  new_roi: 25,
  new_payback_months: 18,
  formula_used: 'test',
};

describe('useC1Stream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    evaluateWhatIfMock.mockResolvedValue(whatIfResult);
  });

  it('handleSliderChange evaluates with the latest businessCaseData after rerender', async () => {
    const adjustment = { name: 'cost', value: 120, original_value: 100 };
    const { result, rerender } = renderHook(
      ({ businessCaseData }: { businessCaseData?: Record<string, unknown> }) =>
        useC1Stream({ businessCaseId: 'bc-1', businessCaseData }),
      { initialProps: { businessCaseData: undefined as Record<string, unknown> | undefined } }
    );

    // Simulate the business case data arriving after the initial render.
    const loadedData = { deal_size: 500000 };
    rerender({ businessCaseData: loadedData });

    await act(async () => {
      await result.current.handleSliderChange(adjustment);
    });

    expect(evaluateWhatIfMock).toHaveBeenCalledWith('bc-1', [adjustment], loadedData);
  });

  it('handleSliderChange surfaces API failures in state.error', async () => {
    evaluateWhatIfMock.mockRejectedValueOnce(new Error('formula API down'));
    const { result } = renderHook(() =>
      useC1Stream({ businessCaseId: 'bc-1', businessCaseData: { deal_size: 1 } })
    );

    await act(async () => {
      await result.current.handleSliderChange({ name: 'cost', value: 2, original_value: 1 });
    });

    expect(result.current.state.error).toBe('formula API down');
    expect(result.current.state.isStreaming).toBe(false);
  });
});
