export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  document_id: string | null;
  date_of_birth: string | null;
  phone_number: string | null;
  email: string | null;
  is_active: boolean;
}
