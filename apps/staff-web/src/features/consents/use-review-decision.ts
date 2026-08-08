import type { Schemas } from '@medical-platform/api-client';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';

export type ConsentReviewDecision = Schemas['ConsentReviewDecision'];
export type ConsentSubmissionReview = Schemas['ConsentSubmissionReviewRead'];

interface ReviewDecisionInput {
  submissionId: string;
  decision: ConsentReviewDecision;
  rationale: string;
}

export function useReviewDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ submissionId, decision, rationale }: ReviewDecisionInput) =>
      apiFetch<ConsentSubmissionReview>(`/api/v1/consents/submissions/${submissionId}/review`, {
        method: 'POST',
        body: JSON.stringify({ decision, rationale }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['consent-requests'] });
    },
  });
}
