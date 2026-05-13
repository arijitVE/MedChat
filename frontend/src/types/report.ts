export type LifecycleStatus =
  | 'uploaded'
  | 'processing'
  | 'auto_approved'
  | 'hitl_required'
  | 'patient_verified'
  | 'doctor_verified'
  | 'fully_verified'
  | 'verified'
  | 'released'
  | 'failed';

export type FieldPipelineStatus = 'auto' | 'hitl' | 'missing';

export interface Report {
  report_id: string;
  job_id: string;
  patient_id: string;
  uploaded_by: string;
  file_name: string;
  display_report_name?: string | null;
  patient_name?: string | null;
  patient_uid?: string | null;
  doctor_id?: string | null;
  doctor_name?: string | null;
  assigned_doctor_id?: string | null;
  assigned_doctor_name?: string | null;
  file_mime: string;
  upload_document_type: string;
  inferred_document_type: string;
  lifecycle_status: LifecycleStatus;
  released_to_patient: boolean;
  first_uploaded_at: string;
  last_edited_at: string | null;
  upload_count: number;
  is_duplicate: boolean;
  duplicate_of: string | null;
  duplicate_warning?: DuplicateWarning | null;
}

export interface ReportDetailResponse {
  report: Report;
  fields: ReportField[];
}

export interface DuplicateWarning {
  type: 'probable';
  existing_report_id: string;
  existing_uploaded_at: string;
  uploaded_by_role: 'doctor' | 'patient';
  message: string;
}

export interface UploadResponse {
  report_id: string;
  status: string;
  patient_uid: string | null;
  duplicate_warning: DuplicateWarning | null;
}

export interface ExactDuplicateError {
  detail: string;
  duplicate_type: 'exact';
  existing_report_id: string;
  existing_uploaded_at: string;
  uploaded_by_role: 'doctor' | 'patient';
  uploaded_by_user_id: string;
}

export interface ReportField {
  field_name: string;
  value: string | null;
  display_value: string;
  is_value_hidden?: boolean;
  numeric_value: number | null;
  unit: string | null;
  reference_range: string | null;
  ref_low: number | null;
  ref_high: number | null;
  confidence: number;
  pipeline_status: FieldPipelineStatus;
  patient_verified: boolean;
  doctor_verified: boolean;
  is_final: boolean;
  eda_available: boolean;
  is_abnormal: boolean | null;
}

export interface FieldVerifyRequest {
  verification_type: 'approved' | 'edited' | 'rejected';
  edited_value?: string;
  edit_reason?: string;
}

export interface FieldEditRequest {
  edited_value: string;
  edit_reason?: string;
}

export interface ReportVerificationResponse {
  report_id: string;
  status: LifecycleStatus | string;
  verified_fields: number;
}

export interface DoctorDashboard {
  patient_count: number;
  recent_uploads: Report[];
  hitl_count: number;
}

export interface DoctorHITLQueueItem {
  report_id: string;
  job_id: string;
  patient_id: string;
  doctor_id: string | null;
  file_name: string;
  lifecycle_status: LifecycleStatus;
  hitl_count: number;
  first_uploaded_at: string;
}

export interface ReportEdaResult {
  report_id: string;
  chart_json: {
    type: 'bar_chart';
    data: {
      fields: string[];
      values: string[];
    };
    meta: {
      patient_id: string;
      hidden_fields: string[];
    };
  };
}
