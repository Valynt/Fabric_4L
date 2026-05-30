import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { createWrapperWithRouterPath } from '@/test-utils';
import { useWorkflowContext } from './useWorkflowContext';

describe('useWorkflowContext', () => {
  it('reads accountId and sessionId from URL params (success path)', () => {
    const wrapper = createWrapperWithRouterPath('/accounts/new?wfAccountId=url-account&wfSessionId=url-session&wfStep=4');
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.accountId).toBe('url-account');
    expect(result.current.sessionId).toBe('url-session');
    expect(result.current.step?.stepIndex).toBe(4);
  });

  it('returns default step object when params are absent', () => {
    const wrapper = createWrapperWithRouterPath('/accounts/new');
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(result.current.accountId).toBeUndefined();
    expect(result.current.sessionId).toBeUndefined();
    expect(result.current.step).toEqual({ stepIndex: 0, stepKey: 'unknown', activeTab: undefined });
  });

  it('propagates invalid numeric step as NaN (error-like branch)', () => {
    const wrapper = createWrapperWithRouterPath('/accounts/new?wfStep=not-a-number');
    const { result } = renderHook(() => useWorkflowContext(), { wrapper });

    expect(Number.isNaN(result.current.step?.stepIndex)).toBe(true);
  });
});
