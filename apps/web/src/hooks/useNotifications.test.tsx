import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import { apiClient } from '@/api/client';
import { createMockResponse, createWrapper } from '../test-utils';
import { QK } from './queryKeys';
import {
  useCreateNotification,
  useMarkNotificationRead,
  useNotifications,
  type NotificationRecord,
} from './useNotifications';

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const sampleNotification: NotificationRecord = {
  id: 'notif-001',
  account_id: 'acct-1',
  subject_id: 'task-1',
  subject_type: 'task',
  type: 'task_created',
  title: 'Task created',
  message: 'Task created: Attach benchmark source',
  read: false,
  created_at: '2026-05-11T12:00:00Z',
  updated_at: '2026-05-11T12:00:00Z',
};

describe('useNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lists notifications with filters', async () => {
    (apiClient.get as Mock).mockResolvedValueOnce(createMockResponse({ items: [sampleNotification], total: 1, unread_count: 1 }));

    const { result } = renderHook(() => useNotifications({ read: false, accountId: 'acct-1' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith('l4', '/notifications?read=false&account_id=acct-1');
    expect(result.current.data?.unread_count).toBe(1);
  });

  it('creates a notification and invalidates notification lists', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    function Wrapper({ children }: { children: React.ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }

    (apiClient.post as Mock).mockResolvedValueOnce(createMockResponse(sampleNotification));

    const { result } = renderHook(() => useCreateNotification(), { wrapper: Wrapper });

    await result.current.mutateAsync({
      type: 'task_created',
      title: 'Task created',
      message: 'Task created: Attach benchmark source',
      account_id: 'acct-1',
      subject_type: 'task',
      subject_id: 'task-1',
    });

    expect(apiClient.post).toHaveBeenCalledWith('l4', '/notifications', {
      type: 'task_created',
      title: 'Task created',
      message: 'Task created: Attach benchmark source',
      account_id: 'acct-1',
      subject_type: 'task',
      subject_id: 'task-1',
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: QK.notifications.all });
  });

  it('marks a notification read and invalidates notification lists', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    function Wrapper({ children }: { children: React.ReactNode }) {
      return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
    }

    (apiClient.patch as Mock).mockResolvedValueOnce(
      createMockResponse({ ...sampleNotification, read: true }),
    );

    const { result } = renderHook(() => useMarkNotificationRead(), { wrapper: Wrapper });

    await result.current.mutateAsync('notif-001');

    expect(apiClient.patch).toHaveBeenCalledWith('l4', '/notifications/notif-001/read', undefined);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: QK.notifications.all });
  });
});

describe('useNotifications filter edge cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests the bare /notifications path when no filters are provided', async () => {
    (apiClient.get as Mock).mockResolvedValueOnce(createMockResponse({ items: [], total: 0, unread_count: 0 }));

    const { result } = renderHook(() => useNotifications(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith('l4', '/notifications');
  });
});
