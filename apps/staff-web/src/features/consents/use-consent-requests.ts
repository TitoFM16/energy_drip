import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { ConsentRequest, ConsentRequestDetail } from './types';

export function useConsentRequests(patientId?: string) {
  return useQuery({
    queryKey: ['consent-requests', patientId ?? null],
    queryFn: () =>
      apiFetch<ConsentRequest[]>(
        `/api/v1/consents/requests${patientId ? `?patient_id=${patientId}` : ''}`,
      ),
  });
}

export function useConsentRequestDetail(requestId: string | null) {
  return useQuery({
    queryKey: ['consent-requests', 'detail', requestId],
    queryFn: () => apiFetch<ConsentRequestDetail>(`/api/v1/consents/requests/${requestId}`),
    enabled: requestId !== null,
  });
}

interface CreateConsentRequestInput {
  patient_id: string;
  template_version_id: string;
}

interface CreateConsentRequestResponse {
  consent_request_id: string;
  token: string;
}

export function useCreateConsentRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ patient_id, template_version_id }: CreateConsentRequestInput) =>
      apiFetch<CreateConsentRequestResponse>(
        `/api/v1/consents/requests?patient_id=${patient_id}&template_version_id=${template_version_id}`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['consent-requests'] });
    },
  });
}
