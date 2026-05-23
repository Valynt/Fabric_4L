import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/api/typedClient';
import { QK } from './queryKeys';
import { safeAsync } from '@/lib/async';
import { createLogger } from '@/lib/telemetry';

const log = createLogger('useComments');

export interface CommentRecord {
  id: string;
  account_id?: string | null;
  subject_type: string;
  subject_id: string;
  body: string;
  author: string;
  created_at: string;
  updated_at: string;
}

export interface CommentListResponse {
  items: CommentRecord[];
  total: number;
}

export interface CommentListFilters {
  subjectType?: string;
  subjectId?: string;
  accountId?: string;
}

export interface CreateCommentInput {
  account_id?: string;
  subject_type: string;
  subject_id: string;
  body: string;
}

function buildCommentListPath(filters: CommentListFilters): string {
  const params = new URLSearchParams();
  if (filters.subjectType) params.set('subject_type', filters.subjectType);
  if (filters.subjectId) params.set('subject_id', filters.subjectId);
  if (filters.accountId) params.set('account_id', filters.accountId);
  const query = params.toString();
  return query ? `/comments?${query}` : '/comments';
}

export function useComments(filters: CommentListFilters = {}) {
  return useQuery({
    queryKey: QK.comments.list(filters),
    queryFn: async () => {
      const response = await apiGet<CommentListResponse>('l4', buildCommentListPath(filters));
      return response.data;
    },
  });
}

export function useCreateComment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateCommentInput) => {
      const response = await apiPost<CommentRecord>('l4', '/comments', input);
      return response.data;
    },
    onSuccess: () => {
      safeAsync(queryClient.invalidateQueries({ queryKey: QK.comments.all }), "comments.invalidate");
    },
    onError: (error) => {
      log.error('CreateComment failed', { error: error instanceof Error ? error.message : String(error) });
    },
  });
}
