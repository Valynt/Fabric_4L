import { beforeEach, describe, expect, it } from 'vitest';
import { useAccountContextStore } from './accountContextStore';

describe('accountContextStore', () => {
  beforeEach(() => {
    useAccountContextStore.setState({ selectedAccountId: null });
  });

  it('has expected initial state', () => {
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
  });

  it('sets and clears selected account', () => {
    const store = useAccountContextStore.getState();
    store.setSelectedAccountId('acct_123');
    expect(useAccountContextStore.getState().selectedAccountId).toBe('acct_123');

    store.clearSelectedAccountId();
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
  });

  it('supports explicit null payload as clear flow', () => {
    useAccountContextStore.getState().setSelectedAccountId('acct_123');
    useAccountContextStore.getState().setSelectedAccountId(null);
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
  });
});
