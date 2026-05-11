export type AssignmentStatus = 'pending' | 'active' | 'rejected';

export interface Assignment {
  assignment_id: string;
  doctor_id: string;
  patient_id: string;
  assigned_by: 'admin' | 'doctor' | 'patient';
  status: AssignmentStatus;
  created_at: string;
  updated_at: string;
}

export interface DoctorProfile {
  user_id: string;
  full_name: string;
  email: string;
  license_number: string | null;
  specialization: string | null;
}

export interface PatientProfile {
  user_id: string;
  full_name: string;
  email: string;
  patient_uid: string;
  date_of_birth: string | null;
  sex: string | null;
}

export interface PatientAssignmentRequest {
  doctor_id: string;
}

export interface DoctorAssignmentInviteRequest {
  patient_uid: string;
}

export type AssignmentRequest = PatientAssignmentRequest | DoctorAssignmentInviteRequest;
