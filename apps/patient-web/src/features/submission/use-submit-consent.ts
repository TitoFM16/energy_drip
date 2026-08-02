import type { Schemas } from '@medical-platform/api-client';
import { useMutation } from '@tanstack/react-query';
import { apiFetch } from '../../shared/api';
import type { ConsentQuestion } from '../token-validation/use-consent-form';

export interface SubmitConsentInput {
  token: string;
  questions: ConsentQuestion[];
  answers: Record<string, unknown>;
  signatureSvg: string;
}

export type ConsentSubmissionResult = Schemas['ConsentSubmissionResult'];
export type ConsentSubmissionPayload = Schemas['ConsentSubmissionCreate'];

export function buildSubmissionPayload(
  questions: ConsentQuestion[],
  answers: Record<string, unknown>,
  signatureSvg: string,
  timezone: string,
): ConsentSubmissionPayload {
  return {
    answers: questions.map((q) => ({
      question_id: q.id,
      field_key: q.field_key,
      value: answers[q.field_key] ?? null,
    })),
    signature_svg: signatureSvg,
    timezone,
  };
}

export function useSubmitConsent() {
  return useMutation({
    mutationFn: ({ token, questions, answers, signatureSvg }: SubmitConsentInput) =>
      apiFetch<ConsentSubmissionResult>(`/api/v1/public/consents/${token}/submit`, {
        method: 'POST',
        body: JSON.stringify(
          buildSubmissionPayload(
            questions,
            answers,
            signatureSvg,
            Intl.DateTimeFormat().resolvedOptions().timeZone,
          ),
        ),
      }),
  });
}
