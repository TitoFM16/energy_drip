import type { ConsentQuestion } from '../token-validation/use-consent-form';

/**
 * A required question only counts as answered once it has a non-null,
 * non-undefined value. The loose `== null` check is intentional: it treats
 * `false`, `0`, and `''` as real answers (a boolean "No" or a numeric "0"
 * is a completed answer, not a missing one) — only an actually-untouched
 * field should block submission.
 */
export function hasIncompleteRequiredAnswers(
  questions: ConsentQuestion[],
  answers: Record<string, unknown>,
): boolean {
  return questions.some((question) => question.is_required && answers[question.field_key] == null);
}
