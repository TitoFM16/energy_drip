import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Medication } from './types';

export function useMedications(patientId: string) {
  return useQuery({
    queryKey: ['medications', patientId],
    queryFn: () => apiFetch<Medication[]>(`/api/v1/patients/${patientId}/medications`),
    enabled: patientId.length > 0,
  });
}

interface CreateMedicationInput {
  patient_id: string;
  name: string;
  dosage?: string;
}

export function useCreateMedication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateMedicationInput) =>
      apiFetch<Medication>('/api/v1/patients/medications', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (medication) => {
      void queryClient.invalidateQueries({ queryKey: ['medications', medication.patient_id] });
    },
  });
}

interface UpdateMedicationInput {
  medicationId: string;
  name?: string;
  dosage?: string;
  is_current?: boolean;
}

export function useUpdateMedication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ medicationId, ...body }: UpdateMedicationInput) =>
      apiFetch<Medication>(`/api/v1/patients/medications/${medicationId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (medication) => {
      void queryClient.invalidateQueries({ queryKey: ['medications', medication.patient_id] });
    },
  });
}
