import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Practitioner } from './types';

export function usePractitioners() {
  return useQuery({
    queryKey: ['practitioners'],
    queryFn: () => apiFetch<Practitioner[]>('/api/v1/practitioners'),
  });
}
