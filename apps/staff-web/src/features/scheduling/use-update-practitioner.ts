import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Practitioner } from './types';

interface UpdatePractitionerInput {
  practitionerId: string;
  specialty?: string;
  is_active?: boolean;
}

export function useUpdatePractitioner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ practitionerId, ...body }: UpdatePractitionerInput) =>
      apiFetch<Practitioner>(`/api/v1/practitioners/${practitionerId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['practitioners'] });
    },
  });
}
