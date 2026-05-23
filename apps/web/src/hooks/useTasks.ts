import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPatch, apiPost } from '@/api/typedClient';
import { QK } from './queryKeys';
import { safeAsync } from '@/lib/async';
import { createLogger } from '@/lib/telemetry';

const log = createLogger('useTasks');

export type TaskStatus = 'open' | 'in_progress' | 'completed';

export interface TaskRecord {
  id: string;
  title: string;
  account_id?: string | null;
  assignee?: string | null;
  due_date?: string | null;
  stage?: string | null;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: TaskRecord[];
  total: number;
}

export interface TaskListFilters {
  accountId?: string;
  status?: TaskStatus;
}

export interface CreateTaskInput {
  title: string;
  account_id?: string;
  assignee?: string;
  due_date?: string;
  stage?: string;
}

export interface UpdateTaskInput {
  taskId: string;
  status?: TaskStatus;
  assignee?: string;
  due_date?: string;
  stage?: string;
}

function buildTaskListPath(filters: TaskListFilters): string {
  const params = new URLSearchParams();
  if (filters.accountId) params.set('account_id', filters.accountId);
  if (filters.status) params.set('status', filters.status);
  const query = params.toString();
  return query ? `/tasks?${query}` : '/tasks';
}

export function useTasks(filters: TaskListFilters = {}) {
  return useQuery({
    queryKey: QK.tasks.list(filters),
    queryFn: async () => {
      const response = await apiGet<TaskListResponse>('l4', buildTaskListPath(filters));
      return response.data;
    },
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateTaskInput) => {
      const response = await apiPost<TaskRecord>('l4', '/tasks', input);
      return response.data;
    },
    onSuccess: () => {
      safeAsync(queryClient.invalidateQueries({ queryKey: QK.tasks.all }), "tasks.invalidate");
    },
    onError: (error) => {
      log.error('CreateTask failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ taskId, ...input }: UpdateTaskInput) => {
      const response = await apiPatch<TaskRecord>('l4', `/tasks/${taskId}`, input);
      return response.data;
    },
    onSuccess: () => {
      safeAsync(queryClient.invalidateQueries({ queryKey: QK.tasks.all }), "tasks.invalidate");
    },
    onError: (error) => {
      log.error('UpdateTask failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
