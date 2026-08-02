import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { Appointment } from './types';

interface CreateAppointmentInput {
  patient_id: string;
  practitioner_id: string;
  starts_at: string;
  ends_at: string;
  notes?: string;
}

export function useCreateAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAppointmentInput) =>
      apiFetch<Appointment>('/api/v1/appointments', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['appointments'] });
      void queryClient.invalidateQueries({ queryKey: ['availability'] });
    },
  });
}
