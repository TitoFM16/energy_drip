import { describe, expect, it } from 'vitest';
import type { ConsentQuestion } from '../token-validation/use-consent-form';
import { hasIncompleteRequiredAnswers } from './validation';

function question(overrides: Partial<ConsentQuestion>): ConsentQuestion {
  return {
    id: 'q1',
    field_key: 'pregnant',
    prompt: '¿Estás embarazada?',
    question_type: 'boolean',
    display_order: 0,
    is_required: true,
    options: [],
    ...overrides,
  };
}

describe('hasIncompleteRequiredAnswers', () => {
  it('is true when a required question has no answer at all', () => {
    expect(hasIncompleteRequiredAnswers([question({})], {})).toBe(true);
  });

  it('is true when a required question is explicitly null or undefined', () => {
    expect(hasIncompleteRequiredAnswers([question({})], { pregnant: null })).toBe(true);
    expect(hasIncompleteRequiredAnswers([question({})], { pregnant: undefined })).toBe(true);
  });

  it('is false once every required question has any non-null value', () => {
    expect(hasIncompleteRequiredAnswers([question({})], { pregnant: true })).toBe(false);
  });

  it('treats false, 0, and empty string as real answers, not missing ones', () => {
    expect(hasIncompleteRequiredAnswers([question({})], { pregnant: false })).toBe(false);
    expect(
      hasIncompleteRequiredAnswers([question({ field_key: 'age', question_type: 'number' })], {
        age: 0,
      }),
    ).toBe(false);
    expect(
      hasIncompleteRequiredAnswers([question({ field_key: 'notes', question_type: 'text' })], {
        notes: '',
      }),
    ).toBe(false);
  });

  it('ignores optional questions entirely', () => {
    expect(hasIncompleteRequiredAnswers([question({ is_required: false })], {})).toBe(false);
  });

  it('is true if any one of several required questions is missing', () => {
    const questions = [
      question({ id: 'q1', field_key: 'pregnant' }),
      question({ id: 'q2', field_key: 'allergies', question_type: 'text' }),
    ];
    expect(hasIncompleteRequiredAnswers(questions, { pregnant: true })).toBe(true);
    expect(hasIncompleteRequiredAnswers(questions, { pregnant: true, allergies: 'Ninguna' })).toBe(
      false,
    );
  });
});
