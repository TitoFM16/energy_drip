export interface Practitioner {
  id: string;
  user_id: string;
  specialty: string | null;
  is_active: boolean;
  full_name: string;
  email: string;
}

export interface AvailableSlot {
  starts_at: string;
  ends_at: string;
}

export type AppointmentStatus =
  | 'scheduled'
  | 'confirmed'
  | 'consent_pending'
  | 'consent_completed'
  | 'checked_in'
  | 'completed'
  | 'cancelled'
  | 'no_show';

export interface Appointment {
  id: string;
  patient_id: string;
  practitioner_id: string;
  starts_at: string;
  ends_at: string;
  status: AppointmentStatus;
  notes: string | null;
}
