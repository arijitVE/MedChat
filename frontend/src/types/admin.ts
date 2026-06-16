export interface AdminStats {
  total_doctors: number;
  total_patients: number;
  total_reports: number;
  reports_processing: number;
  reports_hitl_required: number;
  reports_fully_verified: number;
  assignments_active: number;
  assignments_pending: number;
}

export interface UserListItem {
  user_id: string;
  full_name: string;
  email: string;
  role: 'doctor' | 'patient' | 'admin';
  phone: string | null;
  age: number | null;
  gender: string | null;
  blood_group: string | null;
  allergies: string | null;
  chronic_conditions: string | null;
  address: string | null;
  emergency_contact: string | null;
  last_login: string | null;
  patient_uid: string | null;
  license_number: string | null;
  specialization: string | null;
  hospital_name: string | null;
  years_of_experience: number | null;
  department: string | null;
  profile_photo: string | null;
  verification_status: string | null;
  verification_rejection_reason: string | null;
  date_of_birth: string | null;
  sex: string | null;
  is_registered: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminAssignment {
  assignment_id: string;
  doctor_id: string;
  doctor_name?: string;
  patient_id: string;
  patient_name?: string;
  patient_uid?: string | null;
  assigned_by: 'admin' | 'doctor' | 'patient';
  status: 'pending' | 'active' | 'rejected';
  created_at: string;
  updated_at: string;
}

export interface AdminReportItem {
  report_id: string;
  job_id: string;
  patient_id: string;
  patient_name: string | null;
  doctor_id: string | null;
  doctor_name: string | null;
  uploaded_by: string;
  file_name: string;
  upload_document_type: string;
  inferred_document_type: string | null;
  lifecycle_status: string;
  released_to_patient: boolean;
  first_uploaded_at: string;
}

export interface HITLQueueItem {
  report_id: string;
  job_id: string;
  patient_id: string;
  doctor_id: string | null;
  file_name: string;
  lifecycle_status: string;
  hitl_count: number;
  first_uploaded_at: string;
}

export interface FailedJobItem {
  job_id: string;
  report_id: string | null;
  patient_id: string | null;
  file_name: string | null;
  status: string;
  lifecycle_status: string | null;
  error_message: string | null;
  uploaded_at: string | null;
  processed_at: string | null;
}

export interface AdminMetricRow {
  label: string;
  value: number;
}

export interface AdminAnalytics {
  total_users: number;
  total_doctors: number;
  total_patients: number;
  total_reports: number;
  failed_jobs: number;
  hitl_required: number;
  reports_by_status: AdminMetricRow[];
  users_by_role: AdminMetricRow[];
  reports_by_document_type: AdminMetricRow[];
}

export interface AuditLogItem {
  log_id: string;
  user_id: string | null;
  user_role: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  report_id: string | null;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminNotificationItem {
  notification_id: string;
  recipient_id: string;
  recipient_name?: string | null;
  sender_id: string | null;
  sender_name?: string | null;
  type: string;
  title: string;
  message: string;
  report_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface SystemHealth {
  api_status: string;
  database_status: string;
  total_processing_reports: number;
  total_failed_reports: number;
  total_failed_jobs: number;
}

export interface SystemSettings {
  storage_path: string;
  max_file_size_mb: number;
  jwt_expiry_minutes: number;
  rate_limit_storage: string;
  openai_configured: boolean;
}

export interface PasswordResetRequest {
  user_id: string;
  new_password: string;
}
