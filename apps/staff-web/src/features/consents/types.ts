import type { Schemas } from '@medical-platform/api-client';

export type QuestionType = 'boolean' | 'single_choice' | 'multiple_choice' | 'text' | 'number';

export type ConsentQuestionOptionInput = Schemas['ConsentQuestionOptionInput'];
export type ConsentQuestionInput = Schemas['ConsentQuestionInput'];
export type ConsentTemplateVersion = Schemas['ConsentTemplateVersionRead'];
export type ConsentTemplate = Schemas['ConsentTemplateRead'];
export type ConsentRequestStatus = Schemas['ConsentRequestStatus'];
export type EligibilityResult = Schemas['EligibilityResult'];
export type ConsentRequest = Schemas['ConsentRequestRead'];
export type ConsentAnswer = Schemas['ConsentAnswerRead'];
export type ConsentSubmission = Schemas['ConsentSubmissionRead'];
export type ConsentRequestDetail = Schemas['ConsentRequestDetail'];
export type Document = Schemas['DocumentRead'];
export type DocumentDownload = Schemas['DocumentDownloadRead'];
export type DocumentVerifyResult = Schemas['DocumentVerifyResult'];

// Not generated from Schemas: the backend's ConsentQuestionPublic response
// model types `options` as a loose `dict[str, str]` rather than a
// structured {value, label} model, so openapi-typescript can only infer
// `{[key: string]: string}[]` for it — technically compatible but far
// less useful than this hand-typed version. Worth fixing on the backend
// (a real Pydantic sub-model for question options) so this can switch to
// the generated type like everything else in this file did.
export interface ConsentQuestionPublic {
  id: string;
  field_key: string;
  prompt: string;
  question_type: QuestionType;
  display_order: number;
  is_required: boolean;
  options: { value: string; label: string }[];
}

export interface ConsentTemplateVersionDetail extends ConsentTemplateVersion {
  questions: ConsentQuestionPublic[];
}
