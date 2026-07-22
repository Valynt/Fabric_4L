import { describe, it, expect, vi, type Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import { ValueCaseGenerationPanel } from './ValueCaseGenerationPanel';

vi.mock('@/hooks/useValueCaseGenerationInputs', () => ({
  useValueCaseGenerationInputs: vi.fn(),
}));

import { useValueCaseGenerationInputs } from '@/hooks/useValueCaseGenerationInputs';

function mockInputs(overrides: Partial<ReturnType<typeof useValueCaseGenerationInputs>> = {}) {
  return {
    draft: {
      account_id: 'acct-1',
      account_name: 'Acme',
      stakeholders: ['CFO'],
      accepted_evidence: ['Efficiency gap'],
      scenario_assumptions: ['Ramp in Q1'],
      roi_metrics: { three_year_value: '$1.8M', roi: '214%', payback: '9 months' },
      risk_notes: ['Change management'],
    },
    provenance: {},
    isLoading: false,
    isError: false,
    error: null,
    isReady: true,
    ...overrides,
  };
}

describe('ValueCaseGenerationPanel', () => {
  it('renders live inputs and calls onGenerate with the draft', async () => {
    const onGenerate = vi.fn();
    const onClose = vi.fn();
    (useValueCaseGenerationInputs as Mock).mockReturnValue(mockInputs());

    const wrapper = createWrapper();
    render(
      <ValueCaseGenerationPanel
        accountId="acct-1"
        accountName="Acme"
        caseId="case-1"
        isOpen={true}
        onClose={onClose}
        onGenerate={onGenerate}
        isGenerating={false}
      />,
      { wrapper }
    );

    expect(screen.getByRole('heading', { name: 'Generate Value Case' })).toBeInTheDocument();
    expect(screen.getByText('CFO')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /generate value case/i }));

    await waitFor(() => {
      expect(onGenerate).toHaveBeenCalledWith(expect.objectContaining({
        account_id: 'acct-1',
        stakeholders: ['CFO'],
      }));
    });
  });
});
