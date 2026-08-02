import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { AvailableSlot } from './types';

export function useAvailability(
  practitionerId: string | null,
  date: string,
  durationMinutes: number,
) {
  return useQuery({
    queryKey: ['availability', practitionerId, date, durationMinutes],
    queryFn: () =>
      apiFetch<AvailableSlot[]>(
        `/api/v1/appointments/availability?practitioner_id=${practitionerId}&date_from=${date}` +
          `&date_to=${date}&duration_minutes=${durationMinutes}`,
      ),
    enabled: practitionerId !== null,
  });
}
