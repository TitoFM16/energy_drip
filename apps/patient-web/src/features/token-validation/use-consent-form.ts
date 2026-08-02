import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/api';

export type QuestionType = 'boolean' | 'single_choice' | 'multiple_choice' | 'text' | 'number';

// Not generated from @medical-platform/api-client's Schemas: the backend's
// ConsentQuestionPublic/ConsentFormRead response models type `options` as a
// loose `dict[str, str]` rather than a structured {value, label} model, so
// the generated types can only infer `{[key: string]: string}[]` for it —
// technically compatible but far less useful than this hand-typed version.
// Worth fixing on the backend (a real Pydantic sub-model for question
// options) so this can switch to the generated types like staff-web's
// equivalent types did (see its features/consents/types.ts for the same
// note).
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
