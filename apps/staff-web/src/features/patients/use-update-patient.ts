import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Patient } from './types';

interface UpdatePatientInput {
  patientId: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  email?: string;
  is_active?: boolean;
}

export function useUpdatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ patientId, ...body }: UpdatePatientInput) =>
      apiFetch<Patient>(`/api/v1/patients/${patientId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (patient) => {
      void queryClient.invalidateQueries({ queryKey: ['patients'] });
      queryClient.setQueryData(['patients', patient.id], patient);
    },
  });
}
