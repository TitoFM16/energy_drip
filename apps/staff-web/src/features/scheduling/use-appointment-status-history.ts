import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { AppointmentStatusHistoryEntry } from './types';

export function useAppointmentStatusHistory(appointmentId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['appointment-status-history', appointmentId],
    queryFn: () =>
      apiFetch<AppointmentStatusHistoryEntry[]>(
        `/api/v1/appointments/${appointmentId}/status-history`,
      ),
    enabled: enabled && appointmentId.length > 0,
  });
}
