import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { AvailabilityRule } from './types';

export function useAvailabilityRules(practitionerId: string) {
  return useQuery({
    queryKey: ['availability-rules', practitionerId],
    queryFn: () =>
      apiFetch<AvailabilityRule[]>(
        `/api/v1/appointments/availability-rules?practitioner_id=${practitionerId}`,
      ),
    enabled: practitionerId.length > 0,
  });
}

interface CreateAvailabilityRuleInput {
  practitioner_id: string;
  weekday: number;
  start_time: string;
  end_time: string;
}

export function useCreateAvailabilityRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAvailabilityRuleInput) =>
      apiFetch<AvailabilityRule>('/api/v1/appointments/availability-rules', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (rule) => {
      void queryClient.invalidateQueries({
        queryKey: ['availability-rules', rule.practitioner_id],
      });
    },
  });
}

export function useDeleteAvailabilityRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId }: { ruleId: string; practitionerId: string }) =>
      apiFetch<void>(`/api/v1/appointments/availability-rules/${ruleId}`, {
        method: 'DELETE',
      }),
    onSuccess: (_data, { practitionerId }) => {
      void queryClient.invalidateQueries({ queryKey: ['availability-rules', practitionerId] });
    },
  });
}
