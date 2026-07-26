import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import { apiClient } from '@/api/client';
import { createMockResponse, createWrapper } from '../test-utils';
import { QK } from './queryKeys';
import { useCreateTask, useTasks, useUpdateTask, type TaskRecord } from './useTasks';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const sampleTask: TaskRecord = {
  id: 'task-001',
  title: 'Attach benchmark source',
  account_id: 'acct-1',
  assignee: 'Avery Stone',
  due_date: null,
  stage: 'evidence',
  status: 'open',
  created_at: '2026-05-11T12:00:00Z',
  updated_at: '2026-05-11T12:00:00Z',
};

describe('useTasks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lists tasks with account and status filters', async () => {
    (apiClient.get as Mock).mockResolvedValueOnce(createMockResponse({ items: [sampleTask], total: 1 }));

    const { result } = renderHook(() => useTasks({ accountId: 'acct-1', status: 'open' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('l4', '/tasks?account_id=acct-1&status=open');
    expect(result.current.data?.items[0].title).toBe('Attach benchmark source');
  });

  it('creates a task through the canonical task API and invalidates task lists', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    function Wrapper({ children }: { children: React.ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }

    (apiClient.post as Mock).mockResolvedValueOnce(createMockResponse(sampleTask));

    const { result } = renderHook(() => useCreateTask(), { wrapper: Wrapper });

    await result.current.mutateAsync({
      title: 'Attach benchmark source',
      account_id: 'acct-1',
      assignee: 'Avery Stone',
      stage: 'evidence',
    });

    expect(apiClient.post).toHaveBeenCalledWith('l4', '/tasks', {
      title: 'Attach benchmark source',
      account_id: 'acct-1',
      assignee: 'Avery Stone',
      stage: 'evidence',
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: QK.tasks.all });
  });

  it('updates task status and invalidates task lists', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    function Wrapper({ children }: { children: React.ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }

    (apiClient.patch as Mock).mockResolvedValueOnce(
      createMockResponse({ ...sampleTask, status: 'completed' }),
    );

    const { result } = renderHook(() => useUpdateTask(), { wrapper: Wrapper });

    await result.current.mutateAsync({ taskId: 'task-001', status: 'completed' });

    expect(apiClient.patch).toHaveBeenCalledWith('l4', '/tasks/task-001', {
      status: 'completed',
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: QK.tasks.all });
  });
});

describe('useTasks filter edge cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests the bare /tasks path when no filters are provided', async () => {
    (apiClient.get as Mock).mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));

    const { result } = renderHook(() => useTasks(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith('l4', '/tasks');
  });
});
