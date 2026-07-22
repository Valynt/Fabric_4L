import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import { apiClient } from '@/api/client';
import { createMockResponse, createWrapper } from '../test-utils';
import { QK } from './queryKeys';
import { useComments, useCreateComment, type CommentRecord } from './useComments';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const sampleComment: CommentRecord = {
  id: 'comment-001',
  account_id: 'acct-1',
  subject_type: 'business_case',
  subject_id: 'case-1',
  body: 'Please verify the CFO assumption lineage.',
  author: 'reviewer-123',
  created_at: '2026-05-11T12:00:00Z',
  updated_at: '2026-05-11T12:00:00Z',
};

describe('useComments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lists comments with subject and account filters', async () => {
    (apiClient.get as Mock).mockResolvedValueOnce(createMockResponse({ items: [sampleComment], total: 1 }));

    const { result } = renderHook(
      () => useComments({ subjectType: 'business_case', subjectId: 'case-1', accountId: 'acct-1' }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith(
      'l4',
      '/comments?subject_type=business_case&subject_id=case-1&account_id=acct-1',
    );
    expect(result.current.data?.items[0].body).toBe('Please verify the CFO assumption lineage.');
  });

  it('creates a comment through the canonical comment API and invalidates comment lists', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    function Wrapper({ children }: { children: React.ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }

    (apiClient.post as Mock).mockResolvedValueOnce(createMockResponse(sampleComment));

    const { result } = renderHook(() => useCreateComment(), { wrapper: Wrapper });

    await result.current.mutateAsync({
      account_id: 'acct-1',
      subject_type: 'business_case',
      subject_id: 'case-1',
      body: 'Please verify the CFO assumption lineage.',
    });

    expect(apiClient.post).toHaveBeenCalledWith('l4', '/comments', {
      account_id: 'acct-1',
      subject_type: 'business_case',
      subject_id: 'case-1',
      body: 'Please verify the CFO assumption lineage.',
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: QK.comments.all });
  });
});

describe('useComments filter edge cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests the bare /comments path when no filters are provided', async () => {
    (apiClient.get as Mock).mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));

    const { result } = renderHook(() => useComments(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith('l4', '/comments');
  });
});
