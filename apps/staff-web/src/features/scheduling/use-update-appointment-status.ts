import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Appointment, AppointmentStatus } from './types';

interface UpdateAppointmentStatusInput {
  appointmentId: string;
  status: AppointmentStatus;
  reason?: string;
}

export function useUpdateAppointmentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ appointmentId, status, reason }: UpdateAppointmentStatusInput) =>
      apiFetch<Appointment>(`/api/v1/appointments/${appointmentId}/status`, {
        method: 'POST',
        body: JSON.stringify({ status, reason }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['appointments'] });
      void queryClient.invalidateQueries({ queryKey: ['availability'] });
      void queryClient.invalidateQueries({ queryKey: ['appointment-status-history'] });
    },
  });
}
