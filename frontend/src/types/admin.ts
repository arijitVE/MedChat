export interface AdminStats {
  total_doctors: number;
  total_patients: number;
  total_reports: number;
  processing_now: number;
  hitl_pending: number;
  fully_verified: number;
  assignments_active: number;
  assignments_pending: number;
}

export interface HITLQueueItem {
  report_id: string;
  patient_name: string;
  patient_uid: string;
  doctor_name: string;
  report_date: string;
  fields_pending: number;
  days_waiting: number;
}

export interface UserListItem {
  user_id: string;
  full_name: string;
  email: string;
  role: 'doctor' | 'patient' | 'admin';
  patient_uid: string | null;
  license_number: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PasswordResetRequest {
  user_id: string;
  new_password: string;
}
