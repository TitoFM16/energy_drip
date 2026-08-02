import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { TreatmentSession } from './types';

export function useTreatmentSessions(planId: string | null) {
  return useQuery({
    queryKey: ['treatment-sessions', planId],
    queryFn: () => apiFetch<TreatmentSession[]>(`/api/v1/treatments/plans/${planId}/sessions`),
    enabled: planId !== null,
  });
}

interface RecordTreatmentSessionInput {
  treatment_plan_id: string;
  practitioner_id: string;
  session_number: number;
  clinical_evolution?: string;
}

export function useRecordTreatmentSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RecordTreatmentSessionInput) =>
      apiFetch<TreatmentSession>('/api/v1/treatments/sessions', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (treatmentSession) => {
      void queryClient.invalidateQueries({
        queryKey: ['treatment-sessions', treatmentSession.treatment_plan_id],
      });
    },
  });
}
