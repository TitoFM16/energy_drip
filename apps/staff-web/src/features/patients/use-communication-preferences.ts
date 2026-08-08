import type { Schemas } from '@medical-platform/api-client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';

export type CommunicationPreferences = Schemas['PatientCommunicationPreferencesRead'];

export function useCommunicationPreferences(patientId: string) {
  return useQuery({
    queryKey: ['patients', patientId, 'communication-preferences'],
    queryFn: () =>
      apiFetch<CommunicationPreferences>(`/api/v1/patients/${patientId}/communication-preferences`),
  });
}

export function useUpdateCommunicationPreferences(patientId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (whatsappOptOut: boolean) =>
      apiFetch<CommunicationPreferences>(
        `/api/v1/patients/${patientId}/communication-preferences`,
        {
          method: 'PATCH',
          body: JSON.stringify({ whatsapp_opt_out: whatsappOptOut }),
        },
      ),
    onSuccess: (preferences) => {
      queryClient.setQueryData(['patients', patientId, 'communication-preferences'], preferences);
      void queryClient.invalidateQueries({ queryKey: ['patients', patientId] });
      void queryClient.invalidateQueries({ queryKey: ['patients'] });
    },
  });
}
