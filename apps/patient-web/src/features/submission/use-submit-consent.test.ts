import { describe, expect, it } from 'vitest';
import type { ConsentQuestion } from '../token-validation/use-consent-form';
import { buildSubmissionPayload } from './use-submit-consent';

const questions: ConsentQuestion[] = [
  {
    id: 'q1',
    field_key: 'pregnant',
    prompt: '¿Estás embarazada?',
    question_type: 'boolean',
    display_order: 0,
    is_required: true,
    options: [],
  },
  {
    id: 'q2',
    field_key: 'allergies',
    prompt: '¿Tienes alergias conocidas?',
    question_type: 'text',
    display_order: 1,
    is_required: false,
    options: [],
  },
];

describe('buildSubmissionPayload', () => {
  it('maps every question to an answer, keyed by question_id and field_key', () => {
    const payload = buildSubmissionPayload(
      questions,
      { pregnant: false, allergies: 'Ninguna' },
      '<svg></svg>',
      'America/Bogota',
    );

    expect(payload.answers).toEqual([
      { question_id: 'q1', field_key: 'pregnant', value: false },
      { question_id: 'q2', field_key: 'allergies', value: 'Ninguna' },
    ]);
    expect(payload.signature_svg).toBe('<svg></svg>');
    expect(payload.timezone).toBe('America/Bogota');
  });

  it('submits null for a question the patient never answered, rather than omitting it', () => {
    const payload = buildSubmissionPayload(questions, { pregnant: false }, '<svg></svg>', 'UTC');

    expect(payload.answers).toContainEqual({
      question_id: 'q2',
      field_key: 'allergies',
      value: null,
    });
  });

  it('preserves falsy-but-real answers (false, 0, empty string) instead of nulling them out', () => {
    const payload = buildSubmissionPayload(
      questions,
      { pregnant: false, allergies: '' },
      '<svg></svg>',
      'UTC',
    );

    expect(payload.answers).toContainEqual({
      question_id: 'q1',
      field_key: 'pregnant',
      value: false,
    });
    expect(payload.answers).toContainEqual({
      question_id: 'q2',
      field_key: 'allergies',
      value: '',
    });
  });
});
