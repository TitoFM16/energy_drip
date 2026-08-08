import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { NotificationMessage } from './types';

export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => apiFetch<NotificationMessage[]>('/api/v1/notifications'),
  });
}
