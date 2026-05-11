import { z } from 'zod';
import { doctorSpecializations, signupSexValues } from '../types/auth';

export const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

const optionalSignupSexSchema = z.union([z.enum(signupSexValues), z.literal('')]).optional();
const optionalTrimmedString = z.string().trim().optional();

export const signupSchema = z
  .object({
    email: z.string().trim().email('Enter a valid email address'),
    password: z.string().trim().min(8, 'Password must be at least 8 characters'),
    full_name: z.string().trim().min(2, 'Full name required'),
    role: z.enum(['doctor', 'patient']),
    phone: optionalTrimmedString,
    phone_number: optionalTrimmedString,
    gender: optionalSignupSexSchema,
    license_number: optionalTrimmedString,
    specialization: z.enum(doctorSpecializations),
    hospital_name: optionalTrimmedString,
    years_of_experience: optionalTrimmedString,
    department: optionalTrimmedString,
    profile_photo: optionalTrimmedString,
    date_of_birth: optionalTrimmedString,
    sex: optionalSignupSexSchema,
    blood_group: optionalTrimmedString,
    allergies: optionalTrimmedString,
    chronic_conditions: optionalTrimmedString,
    address: optionalTrimmedString,
    emergency_contact: optionalTrimmedString,
    claim_patient_uid: optionalTrimmedString,
  })
  .refine((data) => data.role !== 'doctor' || !!data.license_number?.trim(), {
    message: 'License number is required for doctors',
    path: ['license_number'],
  })
  .refine((data) => data.role !== 'doctor' || !!data.phone_number?.trim(), {
    message: 'Phone number is required for doctors',
    path: ['phone_number'],
  })
  .refine((data) => {
    const value = data.years_of_experience?.trim();
    return !value || /^\d+$/.test(value);
  }, {
    message: 'Years of experience must be a whole number',
    path: ['years_of_experience'],
  })
  .refine((data) => data.role !== 'patient' || !!data.date_of_birth?.trim(), {
    message: 'Date of birth is required for patients',
    path: ['date_of_birth'],
  })
  .refine((data) => data.role !== 'patient' || !!data.gender, {
    message: 'Gender is required for patients',
    path: ['gender'],
  })
  .refine((data) => data.role !== 'patient' || !!data.phone_number?.trim(), {
    message: 'Phone number is required for patients',
    path: ['phone_number'],
  });
