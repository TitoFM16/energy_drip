import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Appointment } from './types';

interface RescheduleAppointmentInput {
  appointmentId: string;
  starts_at: string;
  ends_at: string;
}

export function useRescheduleAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ appointmentId, starts_at, ends_at }: RescheduleAppointmentInput) =>
      apiFetch<Appointment>(`/api/v1/appointments/${appointmentId}/reschedule`, {
        method: 'PATCH',
        body: JSON.stringify({ starts_at, ends_at }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['appointments'] });
      void queryClient.invalidateQueries({ queryKey: ['availability'] });
    },
  });
}
