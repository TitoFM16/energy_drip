import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { TreatmentDefinition } from './types';

export function useTreatmentDefinitions(includeInactive = false) {
  return useQuery({
    queryKey: ['treatment-definitions', { includeInactive }],
    queryFn: () =>
      apiFetch<TreatmentDefinition[]>(
        `/api/v1/treatments/definitions${includeInactive ? '?include_inactive=true' : ''}`,
      ),
  });
}

interface CreateTreatmentDefinitionInput {
  name: string;
  description?: string;
  default_session_count: number;
}

export function useCreateTreatmentDefinition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTreatmentDefinitionInput) =>
      apiFetch<TreatmentDefinition>('/api/v1/treatments/definitions', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['treatment-definitions'] });
    },
  });
}

interface UpdateTreatmentDefinitionInput {
  definitionId: string;
  name?: string;
  description?: string;
  default_session_count?: number;
  is_active?: boolean;
}

export function useUpdateTreatmentDefinition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ definitionId, ...body }: UpdateTreatmentDefinitionInput) =>
      apiFetch<TreatmentDefinition>(`/api/v1/treatments/definitions/${definitionId}`, {
        method: 'PATCH',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['treatment-definitions'] });
    },
  });
}
