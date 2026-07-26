import { z } from 'zod';

export const appointmentSchema = z
  .object({
    patient_id: z.string().uuid(),
    practitioner_id: z.string().uuid(),
    room_id: z.string().uuid().optional(),
    treatment_definition_id: z.string().uuid().optional(),
    starts_at: z.string().datetime(),
    ends_at: z.string().datetime(),
    notes: z.string().optional(),
  })
  .refine((data) => new Date(data.ends_at) > new Date(data.starts_at), {
    message: 'La cita debe terminar después de empezar',
    path: ['ends_at'],
  });

export type AppointmentFormValues = z.infer<typeof appointmentSchema>;
