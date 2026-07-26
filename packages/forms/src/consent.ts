import { z } from 'zod';

export const consentAnswerSchema = z.object({
  question_id: z.string().uuid(),
  field_key: z.string().min(1),
  value: z.unknown(),
});

export const consentSubmissionSchema = z.object({
  answers: z.array(consentAnswerSchema),
  signature_svg: z.string().min(1, 'Falta la firma'),
  timezone: z.string().min(1),
});

export type ConsentSubmissionFormValues = z.infer<typeof consentSubmissionSchema>;
