import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Practitioner } from './types';

interface CreatePractitionerInput {
  user_id: string;
  specialty?: string;
}

export function useCreatePractitioner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreatePractitionerInput) =>
      apiFetch<Practitioner>('/api/v1/practitioners', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['practitioners'] });
    },
  });
}
