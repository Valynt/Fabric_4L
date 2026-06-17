import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ValueNarrativeHome from './ValueNarrativeHome';

const navigateTo = vi.fn();
const createSetup = vi.fn();

vi.mock('@/hooks/useNavigation', () => ({
  useNavigation: () => ({ navigateTo }),
}));

vi.mock('@/hooks/useIngestion', () => ({
  useRecentIngestionJobs: () => ({ data: [], isLoading: false }),
  useIngestionStats: () => ({
    data: { totalDomains: 0, pagesSynthesized: 0, sourcesAnalyzed: 0, avgProcessingTime: 0 },
  }),
}));

vi.mock('@/hooks/useProspectSetupAccount', () => ({
  useProspectSetupAccountCreate: () => ({
    createSetup,
    isSubmitting: false,
  }),
}));

vi.mock('@/components/workspace/ProspectPromptBuilder', () => ({
  ProspectPromptBuilder: ({
    onCreateSetup,
    onNavigateToWorkspace,
  }: {
    onCreateSetup: (payload: Record<string, unknown>) => Promise<{ accountId?: string }>;
    onNavigateToWorkspace: (path: string, accountId: string) => void;
  }) => (
    <button
      type="button"
      onClick={async () => {
        const result = await onCreateSetup({
          companyName: 'Home Created Account',
          companyDomain: 'home-created.example',
          industry: 'Manufacturing',
        });
        if (result.accountId) {
          onNavigateToWorkspace(`/intelligence/${result.accountId}/signals`, result.accountId);
        }
      }}
    >
      Launch Intelligence
    </button>
  ),
}));

describe('ValueNarrativeHome account setup', () => {
  beforeEach(() => {
    navigateTo.mockReset();
    createSetup.mockReset();
    createSetup.mockResolvedValue({ accountId: 'acc-home-created-001' });
  });

  it('uses canonical account creation and routes to created-account overview', async () => {
    const user = userEvent.setup();
    render(<ValueNarrativeHome />);

    await user.click(screen.getByRole('button', { name: /launch intelligence/i }));

    expect(createSetup).toHaveBeenCalledWith(expect.objectContaining({
      companyName: 'Home Created Account',
      companyDomain: 'home-created.example',
    }));
    expect(navigateTo).toHaveBeenCalledWith('intelligence-overview', {
      accountId: 'acc-home-created-001',
    });
  });
});
