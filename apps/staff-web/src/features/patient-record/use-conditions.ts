import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Condition } from './types';

export function useConditions(patientId: string) {
  return useQuery({
    queryKey: ['conditions', patientId],
    queryFn: () => apiFetch<Condition[]>(`/api/v1/patients/${patientId}/conditions`),
    enabled: patientId.length > 0,
  });
}

interface CreateConditionInput {
  patient_id: string;
  name: string;
  diagnosed_on?: string;
  notes?: string;
}

export function useCreateCondition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateConditionInput) =>
      apiFetch<Condition>('/api/v1/patients/conditions', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (condition) => {
      void queryClient.invalidateQueries({ queryKey: ['conditions', condition.patient_id] });
    },
  });
}

interface UpdateConditionInput {
  conditionId: string;
  name?: string;
  diagnosed_on?: string;
  notes?: string;
  is_active?: boolean;
}

export function useUpdateCondition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conditionId, ...body }: UpdateConditionInput) =>
      apiFetch<Condition>(`/api/v1/patients/conditions/${conditionId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: (condition) => {
      void queryClient.invalidateQueries({ queryKey: ['conditions', condition.patient_id] });
    },
  });
}
