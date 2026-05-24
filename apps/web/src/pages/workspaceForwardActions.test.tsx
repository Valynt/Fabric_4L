import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { createWrapperWithRouterPath } from '@/test-utils';
import AssumptionsTab from '@/pages/hypothesis/AssumptionsTab';
import SolutionCostTab from '@/pages/evidence/SolutionCostTab';

const navigateTo = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...(actual as object), useParams: () => ({ accountId: 'acc-123' }) };
});

vi.mock('@/hooks', async () => {
  const actual = await vi.importActual('@/hooks');
  return { ...(actual as object), useNavigation: () => ({ navigateTo }) };
});

vi.mock('@/hooks/useAccounts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useAccounts')>();
  return {
    ...actual,
    useAccount: () => ({ data: { id: 'acc-123', name: 'Acme', industry: 'Tech', annual_revenue: 1000 }, isLoading: false }),
  };
});

vi.mock('@/agui', () => ({ useAgentEvents: () => ({ messages: [], sendMessage: vi.fn(), suggestedActions: [], steps: [], isStreaming: false, metadata: undefined }) }));

describe('workspace primary forward actions', () => {
  it('AssumptionsTab exposes one forward action and routes to calculator with account context', () => {
    const wrapper = createWrapperWithRouterPath('/t/acme/accounts/acc-123/intelligence/assumptions');
    render(<AssumptionsTab />, { wrapper });
    const buttons = screen.getAllByTestId('primary-forward-action');
    expect(buttons).toHaveLength(1);
    fireEvent.click(buttons[0]);
    expect(navigateTo).toHaveBeenCalledWith('calculator', { accountId: 'acc-123' });
  });

  it('SolutionCostTab exposes one forward action and routes to calculator with account context', () => {
    const wrapper = createWrapperWithRouterPath('/t/acme/accounts/acc-123/intelligence/solution-cost');
    render(<SolutionCostTab />, { wrapper });
    const buttons = screen.getAllByTestId('primary-forward-action');
    expect(buttons).toHaveLength(1);
    fireEvent.click(buttons[0]);
    expect(navigateTo).toHaveBeenCalledWith('calculator', { accountId: 'acc-123' });
  });
});
