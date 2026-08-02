export type QuestionType = 'boolean' | 'single_choice' | 'multiple_choice' | 'text' | 'number';

export interface ConsentQuestionOptionInput {
  value: string;
  label: string;
}

export interface ConsentQuestionInput {
  field_key: string;
  prompt: string;
  question_type: QuestionType;
  display_order: number;
  is_required: boolean;
  options: ConsentQuestionOptionInput[];
}

export interface ConsentTemplateVersion {
  id: string;
  template_id: string;
  version_number: number;
  published_at: string | null;
  body_markdown: string;
}

export interface ConsentTemplate {
  id: string;
  name: string;
  is_active: boolean;
  latest_version: ConsentTemplateVersion | null;
}

export type ConsentRequestStatus = 'pending' | 'completed' | 'expired' | 'invalidated';
export type EligibilityResult = 'eligible' | 'requires_manual_review' | 'not_eligible';

export interface ConsentRequest {
  id: string;
  patient_id: string;
  appointment_id: string | null;
  template_version_id: string;
  status: ConsentRequestStatus;
  expires_at: string;
  created_at: string;
}

export interface ConsentAnswer {
  question_id: string;
  field_key: string;
  value: unknown;
}

export interface ConsentSubmission {
  id: string;
  submitted_at: string;
  timezone: string;
  eligibility_result: EligibilityResult;
  has_signature: boolean;
  answers: ConsentAnswer[];
}

export interface ConsentRequestDetail extends ConsentRequest {
  submission: ConsentSubmission | null;
}

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
