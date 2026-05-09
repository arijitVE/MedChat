import { z } from 'zod';
import { doctorSpecializations, signupSexValues } from '../types/auth';

export const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

const optionalSignupSexSchema = z.union([z.enum(signupSexValues), z.literal('')]).optional();

export const signupSchema = z
  .object({
    email: z.string().trim().email('Enter a valid email address'),
    password: z.string().trim().min(8, 'Password must be at least 8 characters'),
    full_name: z.string().trim().min(2, 'Full name required'),
    role: z.enum(['doctor', 'patient']),
    phone: z.string().optional(),
    license_number: z.string().optional(),
    specialization: z.enum(doctorSpecializations),
    date_of_birth: z.string().optional(),
    sex: optionalSignupSexSchema,
    claim_patient_uid: z.string().optional(),
  })
  .refine((data) => data.role !== 'doctor' || !!data.license_number?.trim(), {
    message: 'License number is required for doctors',
    path: ['license_number'],
  });
