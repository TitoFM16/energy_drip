import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Appointment } from '../scheduling/types';

export type { Appointment };

export function useAppointments(start: string, end: string) {
  return useQuery({
    queryKey: ['appointments', start, end],
    queryFn: () =>
      apiFetch<Appointment[]>(
        `/api/v1/appointments?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
      ),
  });
}
