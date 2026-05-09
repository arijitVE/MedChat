import { z } from 'zod';

const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'];
const MAX_SIZE_MB = 50;

export const uploadSchema = z.object({
  patient_uid: z.string().min(1, 'Patient UID is required'),
  file: z
    .instanceof(File)
    .refine((file) => ALLOWED_TYPES.includes(file.type), 'Only PDF, JPEG, PNG, or TIFF allowed')
    .refine((file) => file.size <= MAX_SIZE_MB * 1024 * 1024, `File must be under ${MAX_SIZE_MB}MB`),
});
