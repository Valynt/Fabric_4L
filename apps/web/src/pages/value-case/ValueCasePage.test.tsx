import { describe, it, expect, vi, type Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createWrapper } from '@/test-utils';
import ValueCasePage from './ValueCasePage';

vi.mock('@/hooks/useAccounts', () => ({
  useAccount: vi.fn(),
}));

vi.mock('@/hooks/useWorkspaceCase', () => ({
  useCanonicalCaseId: vi.fn(),
}));

vi.mock('@/hooks/useValueCaseArtifacts', () => ({
  useValueCaseArtifacts: vi.fn(),
}));

vi.mock('@/components/value-case/ValueCaseGenerationPanel', () => ({
  ValueCaseGenerationPanel: vi.fn(() => <div data-testid="generation-panel" />),
}));

import { useAccount } from '@/hooks/useAccounts';
import { useCanonicalCaseId } from '@/hooks/useWorkspaceCase';
import { useValueCaseArtifacts } from '@/hooks/useValueCaseArtifacts';

describe('ValueCasePage', () => {
  it('opens the generation panel instead of using hardcoded inputs', async () => {
    (useAccount as Mock).mockReturnValue({
      data: { id: 'acct-1', name: 'Acme' },
      isLoading: false,
    });
    (useCanonicalCaseId as Mock).mockReturnValue({
      data: 'case-1',
      isLoading: false,
    });
    (useValueCaseArtifacts as Mock).mockReturnValue({
      versions: [],
      isLoadingVersions: false,
      versionsError: null,
      refetch: vi.fn(),
      selectedVersion: null,
      setSelectedVersionId: vi.fn(),
      generateArtifact: { mutate: vi.fn(), isPending: false, isError: false, error: null },
      publishArtifact: { mutate: vi.fn(), isPending: false, isError: false, error: null },
    });

    const wrapper = createWrapper();
    render(<ValueCasePage accountId="acct-1" />, { wrapper });

    fireEvent.click(screen.getByRole('button', { name: /generate/i }));

    await waitFor(() => {
      expect(screen.getByTestId('generation-panel')).toBeInTheDocument();
    });
  });
});
