import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { TreatmentSession } from './types';

export function useFinalizeTreatmentSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch<TreatmentSession>(`/api/v1/treatments/sessions/${sessionId}/finalize`, {
        method: 'POST',
      }),
    onSuccess: (treatmentSession) => {
      void queryClient.invalidateQueries({
        queryKey: ['treatment-sessions', treatmentSession.treatment_plan_id],
      });
    },
  });
}
