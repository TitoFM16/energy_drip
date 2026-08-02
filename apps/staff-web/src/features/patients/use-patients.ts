import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Patient } from './types';

// Same query key as the Patients screen's inline useQuery, so both share one
// cached list instead of issuing duplicate requests.
export function usePatients() {
  return useQuery({
    queryKey: ['patients'],
    queryFn: () => apiFetch<Patient[]>('/api/v1/patients'),
  });
}

export function usePatientSearch(query: string) {
  return useQuery({
    queryKey: ['patients', 'search', query],
    queryFn: () => apiFetch<Patient[]>(`/api/v1/patients?q=${encodeURIComponent(query)}`),
    enabled: query.trim().length >= 2,
  });
}
