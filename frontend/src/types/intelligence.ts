export interface TrendPoint {
  date: string;
  value: string;
  numeric_value: number | null;
  unit: string | null;
  is_abnormal: boolean | null;
}

export interface ChartMeta {
  label: string;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
}

export interface ClinicalField {
  field_id: string;
  job_id: string;
  patient_id: string;
  name: string;
  raw_name: string;
  value: string;
  numeric_value: number | null;
  unit: string | null;
  reference_range: string | null;
  ref_low: number | null;
  ref_high: number | null;
  confidence: number;
  status: string;
  is_abnormal: boolean | null;
}

export interface TrendResult {
  field_name: string;
  patient_id: string;
  data_points: TrendPoint[];
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
  percent_change: number | null;
  chart_json: {
    type: string;
    data: { x: string[]; y: number[] };
    meta: ChartMeta;
  };
  insight: string;
  cached: boolean;
}

export interface ReasoningResult {
  interpretation: string;
  clinical_significance: string;
  possible_conditions: string[];
  critical_flags: string[];
  confidence: number;
  citations: string[];
  cached: boolean;
}

export interface RetrievalResult {
  records: Record<string, unknown>[];
  total_count: number;
  query_interpretation: string;
  retrieval_type: 'filter' | 'semantic';
}

export type DoctorQueryResponse = ReasoningResult | TrendResult | RetrievalResult;

export function isReasoningResult(r: DoctorQueryResponse): r is ReasoningResult {
  return 'interpretation' in r;
}

export function isTrendResult(r: DoctorQueryResponse): r is TrendResult {
  return 'data_points' in r;
}

export function isRetrievalResult(r: DoctorQueryResponse): r is RetrievalResult {
  return 'records' in r;
}

export interface SimplifiedField {
  name: string;
  value: string;
  status: string;
}

export interface PatientChatResult {
  response: string;
  simplified_fields: SimplifiedField[];
  disclaimer: string;
  safety_blocked: boolean;
}

export interface AnalyticsResult {
  patient_id: string;
  analytics_engine?: string;
  overview?: PatientAnalyticsOverview;
  trends?: PatientFieldTrend[];
  critical_changes?: PatientFieldTrend[];
  stable_parameters?: PatientFieldTrend[];
  insufficient_data?: PatientFieldTrend[];
  abnormal_fields: ClinicalField[];
  normal_fields: ClinicalField[];
  abnormal_count: number;
  normal_count: number;
  chart_json: {
    type: string;
    data: {
      fields: string[];
      values: number[];
      ref_low: (number | null)[];
      ref_high: (number | null)[];
    };
    meta: { patient_id: string; date: string };
  };
  ai_insight: string;
  cached: boolean;
}

export interface PatientAnalyticsOverview {
  tracked_fields: number;
  trend_ready_fields: number;
  total_values: number;
  abnormal_latest_count: number;
  critical_change_count: number;
  insufficient_data_count: number;
}

export interface PatientTrendValue {
  value: number | null;
  display_value: string;
  unit: string | null;
  report_date: string;
  display_report_date?: string;
  reference_min: number | null;
  reference_max: number | null;
  reference_range: string | null;
  status: 'low' | 'normal' | 'high' | 'unknown' | string;
  is_abnormal: boolean | null;
  report_id: string;
  report_name: string;
  confidence: number;
}

export interface PatientFieldTrend {
  field_name: string;
  unit: string | null;
  sample_size: number;
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data' | string;
  percent_change: number | null;
  latest_value: number | null;
  latest_display_value: string;
  latest_status: 'low' | 'normal' | 'high' | 'unknown' | string;
  latest_report_date: string;
  latest_reference_min: number | null;
  latest_reference_max: number | null;
  values: PatientTrendValue[];
}

export type DoctorAssistantMode =
  | 'patient_specific'
  | 'global_analytics'
  | 'report_discussion'
  | 'trend_analysis'
  | 'ocr_investigation'
  | 'abnormality_review';

export interface DoctorQueryRequest {
  text: string;
  patient_id?: string;
  mode?: DoctorAssistantMode;
  workflow?: string;
  filters?: Record<string, unknown>;
}

export interface PatientChatRequest {
  text: string;
  patient_id: string;
  context_mode?: 'report' | 'general';
  report_id?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  reasoningResult?: ReasoningResult;
  trendResult?: TrendResult;
  retrievalResult?: RetrievalResult;
  patientResult?: PatientChatResult;
  timestamp: string;
}
