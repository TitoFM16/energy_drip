import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Patient } from './types';

export interface PatientInput {
  first_name: string;
  last_name: string;
  document_id?: string;
  date_of_birth?: string;
  phone_number?: string;
  email?: string;
}

export function useCreatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: PatientInput) =>
      apiFetch<Patient>('/api/v1/patients', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['patients'] });
    },
  });
}
