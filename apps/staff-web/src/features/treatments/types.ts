export interface TreatmentDefinition {
  id: string;
  name: string;
  description: string | null;
  default_session_count: number;
  is_active: boolean;
}

export type TreatmentPlanStatus = 'active' | 'completed' | 'cancelled';

export interface TreatmentPlan {
  id: string;
  patient_id: string;
  treatment_definition_id: string;
  status: TreatmentPlanStatus;
  planned_session_count: number;
  notes: string | null;
}

export interface TreatmentSession {
  id: string;
  treatment_plan_id: string;
  practitioner_id: string;
  session_number: number;
  performed_at: string | null;
  clinical_evolution: string | null;
}
