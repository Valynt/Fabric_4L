import { beforeEach, describe, expect, it } from 'vitest';
import {
  loadAccountContextForTenant,
  saveAccountContextForTenant,
  useAccountContextStore,
} from './accountContextStore';
import {
  _resetClerkSessionForTests,
  setActiveClerkOrgId,
} from '@/auth/clerkSession';

describe('accountContextStore', () => {
  beforeEach(() => {
    sessionStorage.clear();
    _resetClerkSessionForTests();
    useAccountContextStore.setState({
      selectedAccountId: null,
      _persistedTenantId: null,
    });
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

  it('loads tenant-scoped account context from session storage', () => {
    sessionStorage.setItem(
      'fabric-account-context-tenant-a',
      JSON.stringify({ selectedAccountId: 'acct_a' })
    );

    loadAccountContextForTenant('tenant-a');

    expect(useAccountContextStore.getState().selectedAccountId).toBe('acct_a');
  });

  it('clears account context when tenant storage is missing or malformed', () => {
    useAccountContextStore.setState({ selectedAccountId: 'acct_previous' });
    loadAccountContextForTenant('tenant-without-context');
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();

    sessionStorage.setItem('fabric-account-context-tenant-b', '{not-json');
    useAccountContextStore.setState({ selectedAccountId: 'acct_previous' });
    loadAccountContextForTenant('tenant-b');
    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
  });

  it('saves selected account context under the active tenant key', () => {
    useAccountContextStore.setState({ selectedAccountId: 'acct_123' });

    saveAccountContextForTenant('tenant-a');

    expect(
      JSON.parse(sessionStorage.getItem('fabric-account-context-tenant-a') ?? '{}')
    ).toEqual({ selectedAccountId: 'acct_123' });
    expect(sessionStorage.getItem('fabric-account-context-tenant-b')).toBeNull();
  });

  it('syncTenant clears stale selection on active org switch and keeps matching tenant state', () => {
    setActiveClerkOrgId('org_a');
    useAccountContextStore.getState().setSelectedAccountId('acct_a');

    useAccountContextStore.getState().syncTenant();
    expect(useAccountContextStore.getState().selectedAccountId).toBe('acct_a');

    setActiveClerkOrgId('org_b');
    useAccountContextStore.getState().syncTenant();

    expect(useAccountContextStore.getState().selectedAccountId).toBeNull();
    expect(useAccountContextStore.getState()._persistedTenantId).toBe('org_b');
  });
});
