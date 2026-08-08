import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Allergy } from './types';

export function useAllergies(patientId: string) {
  return useQuery({
    queryKey: ['allergies', patientId],
    queryFn: () => apiFetch<Allergy[]>(`/api/v1/patients/${patientId}/allergies`),
    enabled: patientId.length > 0,
  });
}

interface CreateAllergyInput {
  patient_id: string;
  substance: string;
  severity?: string;
  notes?: string;
}

export function useCreateAllergy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAllergyInput) =>
      apiFetch<Allergy>('/api/v1/patients/allergies', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (allergy) => {
      void queryClient.invalidateQueries({ queryKey: ['allergies', allergy.patient_id] });
    },
  });
}

interface UpdateAllergyInput {
  allergyId: string;
  substance?: string;
  severity?: string;
  notes?: string;
  is_active?: boolean;
}

export function useUpdateAllergy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ allergyId, ...body }: UpdateAllergyInput) =>
      apiFetch<Allergy>(`/api/v1/patients/allergies/${allergyId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (allergy) => {
      void queryClient.invalidateQueries({ queryKey: ['allergies', allergy.patient_id] });
    },
  });
}
