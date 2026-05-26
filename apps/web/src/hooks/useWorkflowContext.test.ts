import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createWrapperWithRouterPath } from '@/test-utils';
import { useWorkflowContext } from './useWorkflowContext';
import { useWorkflowStore } from '@/workflow/store/workflowStore';

vi.mock('@/workflow/store/workflowStore', () => ({ useWorkflowStore: vi.fn() }));
const mockUseWorkflowStore = vi.mocked(useWorkflowStore);

const baseContext = {
  accountId: 'store-account',
  sessionId: 'store-session',
  step: { stepIndex: 2, stepKey: 'hypothesis', activeTab: 'trees' },
  workspaceCaseId: 'case-1',
  driverTreeId: 'tree-1',
  scenarioId: 'scenario-1',
  businessCaseId: 'bc-1',
};

describe('useWorkflowContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseWorkflowStore.mockImplementation((selector: never) => selector({ workflowContext: baseContext }));
  });

  it('uses URL params over store values (success path)', () => {
    const wrapper = createWrapperWithRouterPath('/workflow?wfAccountId=url-account&wfSessionId=url-session&wfStep=4');
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.accountId).toBe('url-account');
    expect(result.current.sessionId).toBe('url-session');
    expect(result.current.step?.stepIndex).toBe(4);
  });

  it('falls back to store defaults when params are missing (default path)', () => {
    const wrapper = createWrapperWithRouterPath('/workflow');
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.accountId).toBe('store-account');
    expect(result.current.step?.activeTab).toBe('trees');
  });

  it('propagates invalid numeric branching as NaN (error-like branch)', () => {
    const wrapper = createWrapperWithRouterPath('/workflow?wfStep=not-a-number');
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(Number.isNaN(result.current.step?.stepIndex)).toBe(true);
  });
});
