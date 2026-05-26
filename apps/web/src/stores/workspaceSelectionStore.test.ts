import { beforeEach, describe, expect, it } from 'vitest';
import { useWorkspaceSelectionStore } from './workspaceSelectionStore';

describe('workspaceSelectionStore', () => {
  beforeEach(() => {
    useWorkspaceSelectionStore.setState({ selectionsByAccount: {} });
  });

  it('returns empty selection for unknown account', () => {
    expect(useWorkspaceSelectionStore.getState().getSelection('missing')).toEqual({
      treeId: null,
      valueModelId: null,
    });
  });

  it('stores and reads selection by account id', () => {
    useWorkspaceSelectionStore.getState().setSelection('acct_a', { treeId: 't1', valueModelId: 'v1' });
    useWorkspaceSelectionStore.getState().setSelection('acct_b', { treeId: 't2', valueModelId: null });

    expect(useWorkspaceSelectionStore.getState().getSelection('acct_a')).toEqual({ treeId: 't1', valueModelId: 'v1' });
    expect(useWorkspaceSelectionStore.getState().getSelection('acct_b')).toEqual({ treeId: 't2', valueModelId: null });
  });

  it('replaces selection for same account without mutating other account state', () => {
    const store = useWorkspaceSelectionStore.getState();
    store.setSelection('acct_a', { treeId: 't1', valueModelId: 'v1' });
    store.setSelection('acct_b', { treeId: 't2', valueModelId: 'v2' });
    store.setSelection('acct_a', { treeId: null, valueModelId: 'v3' });

    expect(useWorkspaceSelectionStore.getState().getSelection('acct_a')).toEqual({ treeId: null, valueModelId: 'v3' });
    expect(useWorkspaceSelectionStore.getState().getSelection('acct_b')).toEqual({ treeId: 't2', valueModelId: 'v2' });
  });
});
