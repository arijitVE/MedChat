import { z } from 'zod';

export const verifyFieldSchema = z
  .object({
    verification_type: z.enum(['approved', 'edited', 'rejected']),
    edited_value: z.string().optional(),
    edit_reason: z.string().optional(),
  })
  .refine((data) => data.verification_type !== 'edited' || !!data.edited_value, {
    message: 'Edited value is required when editing',
    path: ['edited_value'],
  });
