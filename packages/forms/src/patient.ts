import { z } from 'zod';

export const patientSchema = z.object({
  first_name: z.string().min(1, 'Requerido'),
  last_name: z.string().min(1, 'Requerido'),
  document_id: z.string().optional(),
  date_of_birth: z.string().date().optional(),
  phone_number: z.string().min(7, 'Número inválido').optional(),
  email: z.string().email().optional(),
});

export type PatientFormValues = z.infer<typeof patientSchema>;
