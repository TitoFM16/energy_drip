import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { StaffUser } from './types';

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => apiFetch<StaffUser[]>('/api/v1/auth/users'),
  });
}
