export const signupSexValues = ['male', 'female', 'other'] as const;
export type SignupSex = (typeof signupSexValues)[number];

export const doctorSpecializations = [
  'General Physician',
  'Cardiologist',
  'Neurologist',
  'Dermatologist',
  'Orthopedic Surgeon',
  'Pediatrician',
  'Gynecologist',
  'Psychiatrist',
  'Radiologist',
  'Oncologist',
] as const;
export type DoctorSpecialization = (typeof doctorSpecializations)[number];

export interface User {
  user_id: string;
  email: string;
  role: 'doctor' | 'patient' | 'admin';
  full_name: string;
  phone?: string | null;
  age?: number | null;
  gender?: SignupSex | string | null;
  blood_group?: string | null;
  allergies?: string | null;
  chronic_conditions?: string | null;
  address?: string | null;
  emergency_contact?: string | null;
  created_at?: string;
  updated_at?: string;
  last_login?: string | null;
  account_status?: string | null;
  patient_uid?: string;
  license_number?: string;
  specialization?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface BackendTokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  role: User['role'];
  refresh_token?: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  role: 'doctor' | 'patient';
  full_name: string;
  phone?: string | null;
  phone_number?: string | null;
  age?: number | null;
  gender?: SignupSex | null;
  license_number?: string | null;
  specialization?: DoctorSpecialization | null;
  date_of_birth?: string | null;
  sex?: SignupSex | null;
  blood_group?: string | null;
  allergies?: string | null;
  chronic_conditions?: string | null;
  address?: string | null;
  emergency_contact?: string | null;
  claim_patient_uid?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}
