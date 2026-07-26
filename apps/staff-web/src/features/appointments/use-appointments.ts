import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';

export interface Appointment {
  id: string;
  patient_id: string;
  practitioner_id: string;
  starts_at: string;
  ends_at: string;
  status: string;
}

export function useAppointments(start: string, end: string) {
  return useQuery({
    queryKey: ['appointments', start, end],
    queryFn: () =>
      apiFetch<Appointment[]>(
        `/api/v1/appointments?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      ),
  });
}
