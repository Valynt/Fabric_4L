import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '@/api/typedClient';
import { QK } from '@/hooks/queryKeys';

interface PauseAllResponse {
  paused_jobs: number;
  status: string;
  message: string;
}

export function usePauseAllExtractions() {
  const queryClient = useQueryClient();

  return useMutation<PauseAllResponse, Error>({
    mutationFn: async () => {
      const response = await apiPost<PauseAllResponse>('l2', '/v1/extract/pause-all', {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QK.extraction.all });
    },
  });
}
