import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Practitioner } from './types';

export function usePractitioners(includeInactive = false) {
  return useQuery({
    queryKey: ['practitioners', { includeInactive }],
    queryFn: () =>
      apiFetch<Practitioner[]>(
        `/api/v1/practitioners${includeInactive ? '?include_inactive=true' : ''}`,
      ),
  });
}
