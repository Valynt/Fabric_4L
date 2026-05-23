import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch, apiPost } from '@/api/typedClient';
import { QK } from './queryKeys';
import { safeAsync } from '@/lib/async';
import { createLogger } from '@/lib/telemetry';

const log = createLogger('useNotifications');

export interface NotificationRecord {
  id: string;
  account_id?: string | null;
  subject_id?: string | null;
  subject_type?: string | null;
  type: string;
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: NotificationRecord[];
  total: number;
  unread_count: number;
}

export interface NotificationListFilters {
  read?: boolean;
  accountId?: string;
}

export interface CreateNotificationInput {
  account_id?: string;
  subject_id?: string;
  subject_type?: string;
  type: string;
  title: string;
  message: string;
}

function buildNotificationListPath(filters: NotificationListFilters): string {
  const params = new URLSearchParams();
  if (filters.read !== undefined) params.set('read', String(filters.read));
  if (filters.accountId) params.set('account_id', filters.accountId);
  const query = params.toString();
  return query ? `/notifications?${query}` : '/notifications';
}

export function useNotifications(filters: NotificationListFilters = {}) {
  return useQuery({
    queryKey: QK.notifications.list(filters),
    queryFn: async () => {
      const response = await apiGet<NotificationListResponse>('l4', buildNotificationListPath(filters));
      return response.data;
    },
  });
}

export function useCreateNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateNotificationInput) => {
      const response = await apiPost<NotificationRecord>('l4', '/notifications', input);
      return response.data;
    },
    onSuccess: () => {
      safeAsync(queryClient.invalidateQueries({ queryKey: QK.notifications.all }), "notifications.invalidate");
    },
    onError: (error) => {
      log.error('CreateNotification failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) => {
      const response = await apiPatch<NotificationRecord>('l4', `/notifications/${notificationId}/read`);
      return response.data;
    },
    onSuccess: () => {
      safeAsync(queryClient.invalidateQueries({ queryKey: QK.notifications.all }), "notifications.invalidate");
    },
    onError: (error) => {
      log.error('MarkNotificationRead failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
