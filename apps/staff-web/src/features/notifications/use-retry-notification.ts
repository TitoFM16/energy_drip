import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { NotificationMessage } from './types';

export function useRetryNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (messageId: string) =>
      apiFetch<NotificationMessage>(`/api/v1/notifications/${messageId}/retry`, {
        method: 'POST',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}
