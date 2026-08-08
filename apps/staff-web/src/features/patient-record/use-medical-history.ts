import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { MedicalHistoryEntry } from './types';

export function useMedicalHistory(patientId: string) {
  return useQuery({
    queryKey: ['medical-history', patientId],
    queryFn: () => apiFetch<MedicalHistoryEntry[]>(`/api/v1/patients/${patientId}/medical-history`),
    enabled: patientId.length > 0,
  });
}

interface CreateMedicalHistoryEntryInput {
  patient_id: string;
  summary: string;
  amends_entry_id?: string;
}

export function useCreateMedicalHistoryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateMedicalHistoryEntryInput) =>
      apiFetch<MedicalHistoryEntry>('/api/v1/patients/medical-history', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (entry) => {
      void queryClient.invalidateQueries({ queryKey: ['medical-history', entry.patient_id] });
    },
  });
}

export function useFinalizeMedicalHistoryEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      apiFetch<MedicalHistoryEntry>(`/api/v1/patients/medical-history/${entryId}/finalize`, {
        method: 'POST',
      }),
    onSuccess: (entry) => {
      void queryClient.invalidateQueries({ queryKey: ['medical-history', entry.patient_id] });
    },
  });
}
