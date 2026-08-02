import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Patient } from './types';

export function usePatient(patientId: string) {
  return useQuery({
    queryKey: ['patients', patientId],
    queryFn: () => apiFetch<Patient>(`/api/v1/patients/${patientId}`),
  });
}
