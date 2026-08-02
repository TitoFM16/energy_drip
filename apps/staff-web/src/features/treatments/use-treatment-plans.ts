import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { TreatmentPlan, TreatmentPlanStatus } from './types';

export function useTreatmentPlans(patientId: string) {
  return useQuery({
    queryKey: ['treatment-plans', patientId],
    queryFn: () => apiFetch<TreatmentPlan[]>(`/api/v1/treatments/plans?patient_id=${patientId}`),
    enabled: patientId.length > 0,
  });
}

interface CreateTreatmentPlanInput {
  patient_id: string;
  treatment_definition_id: string;
  planned_session_count: number;
  notes?: string;
}

export function useCreateTreatmentPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTreatmentPlanInput) =>
      apiFetch<TreatmentPlan>('/api/v1/treatments/plans', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (plan) => {
      void queryClient.invalidateQueries({ queryKey: ['treatment-plans', plan.patient_id] });
    },
  });
}

interface UpdateTreatmentPlanInput {
  planId: string;
  status?: TreatmentPlanStatus;
  notes?: string;
}

export function useUpdateTreatmentPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, ...body }: UpdateTreatmentPlanInput) =>
      apiFetch<TreatmentPlan>(`/api/v1/treatments/plans/${planId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (plan) => {
      void queryClient.invalidateQueries({ queryKey: ['treatment-plans', plan.patient_id] });
    },
  });
}
