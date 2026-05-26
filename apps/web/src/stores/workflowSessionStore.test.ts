import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWorkflowSessionStore } from './workflowSessionStore';

const EMPTY_CONTEXT = {
  accountId: null,
  caseId: null,
  selectedEntityId: null,
  tabId: null,
  lastPath: null,
  updatedAt: null,
};

describe('workflowSessionStore', () => {
  beforeEach(() => {
    useWorkflowSessionStore.setState({ context: EMPTY_CONTEXT });
    vi.useRealTimers();
  });

  it('has expected initial context contract', () => {
    expect(useWorkflowSessionStore.getState().context).toEqual(EMPTY_CONTEXT);
  });

  it('merges partial context updates and stamps updatedAt', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-15T12:00:00.000Z'));

    const store = useWorkflowSessionStore.getState();
    store.setContext({ accountId: 'acct_1', tabId: 'overview' });
    store.setContext({ selectedEntityId: 'entity_9' });

    expect(useWorkflowSessionStore.getState().context).toMatchObject({
      accountId: 'acct_1',
      tabId: 'overview',
      selectedEntityId: 'entity_9',
    });
    expect(useWorkflowSessionStore.getState().context.updatedAt).toBe('2026-01-15T12:00:00.000Z');
  });

  it('clears context for cross-page workflow reset', () => {
    const store = useWorkflowSessionStore.getState();
    store.setContext({ accountId: 'acct_1', caseId: 'case_2', lastPath: '/workspace/details' });
    store.clearContext();
    expect(useWorkflowSessionStore.getState().context).toEqual(EMPTY_CONTEXT);
  });
});
