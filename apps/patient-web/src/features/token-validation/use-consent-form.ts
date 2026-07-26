import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/api';

export type QuestionType = 'boolean' | 'single_choice' | 'multiple_choice' | 'text' | 'number';

export interface ConsentQuestion {
  id: string;
  field_key: string;
  prompt: string;
  question_type: QuestionType;
  display_order: number;
  is_required: boolean;
  options: { value: string; label: string }[];
}

export interface ConsentForm {
  consent_request_id: string;
  template_version_id: string;
  body_markdown: string;
  questions: ConsentQuestion[];
  expires_at: string;
}

export function useConsentForm(token: string | undefined) {
  return useQuery({
    queryKey: ['consent-form', token],
    queryFn: () => apiFetch<ConsentForm>(`/api/v1/public/consents/${token}`),
    enabled: Boolean(token),
    retry: false,
  });
}
