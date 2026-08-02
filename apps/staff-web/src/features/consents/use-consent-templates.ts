import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type {
  ConsentQuestionInput,
  ConsentTemplate,
  ConsentTemplateVersion,
  ConsentTemplateVersionDetail,
} from './types';

export function useConsentTemplates() {
  return useQuery({
    queryKey: ['consent-templates'],
    queryFn: () => apiFetch<ConsentTemplate[]>('/api/v1/consents/templates'),
  });
}

export function useConsentTemplateVersion(versionId: string | null) {
  return useQuery({
    queryKey: ['consent-template-versions', versionId],
    queryFn: () =>
      apiFetch<ConsentTemplateVersionDetail>(`/api/v1/consents/templates/versions/${versionId}`),
    enabled: versionId !== null,
  });
}

interface CreateConsentTemplateInput {
  name: string;
  body_markdown: string;
  questions: ConsentQuestionInput[];
}

export function useCreateConsentTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateConsentTemplateInput) =>
      apiFetch<ConsentTemplate>('/api/v1/consents/templates', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['consent-templates'] });
    },
  });
}

export function usePublishConsentTemplateVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ templateId, versionId }: { templateId: string; versionId: string }) =>
      apiFetch<ConsentTemplateVersion>(
        `/api/v1/consents/templates/${templateId}/versions/${versionId}/publish`,
        { method: 'POST' },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['consent-templates'] });
    },
  });
}
