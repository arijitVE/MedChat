import type { AxiosRequestConfig } from 'axios';
import { apiClient } from './client';
import type {
  FieldVerifyRequest,
  Report,
  ReportDetailResponse,
  ReportEdaResult,
  ReportField,
  UploadResponse,
} from '../types/report';
import type { PatientProfile } from '../types/assignment';
import type { FieldVerification } from '../types/verification';

type RequestOptions = Pick<AxiosRequestConfig, 'signal'>;
type MyReportsParams = {
  date_from?: string;
  date_to?: string;
  document_type?: string;
  lifecycle_status?: string;
  query?: string;
};
type DoctorReportsParams = {
  lifecycle_status?: string;
  patient_id?: string;
  query?: string;
};

export const reportsApi = {
  upload: (formData: FormData, force?: boolean) =>
    apiClient.post<UploadResponse>(
      '/doctor/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' }, params: { force } },
    ),
  doctorUpload: (formData: FormData, force?: boolean) =>
    apiClient.post<UploadResponse>(
      '/doctor/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' }, params: { force } },
    ),
  getDoctorReports: (params?: DoctorReportsParams) =>
    apiClient.get<Report[]>('/doctor/reports/search', {
      params: {
        lifecycle_status: params?.lifecycle_status,
        patient_id: params?.patient_id,
        query: params?.query,
      },
    }),
  fetchDoctorReports: (params?: DoctorReportsParams) =>
    apiClient.get<Report[]>('/doctor/reports/search', {
      params: {
        lifecycle_status: params?.lifecycle_status,
        patient_id: params?.patient_id,
        query: params?.query,
      },
    }),
  getReport: (reportId: string) =>
    apiClient.get<ReportDetailResponse>(`/doctor/reports/${reportId}`),
  fetchDoctorReport: (reportId: string) =>
    apiClient.get<ReportDetailResponse>(`/doctor/reports/${reportId}`),
  getDoctorRawReport: (reportId: string) =>
    apiClient.get<Blob>(`/doctor/reports/${reportId}/raw-file`, {
      responseType: 'blob',
    }),
  getReportFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/doctor/reports/${reportId}/fields`),
  fetchDoctorFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/doctor/reports/${reportId}/fields`),
  releaseToPatient: (reportId: string) =>
    apiClient.post<Report>(`/doctor/reports/${reportId}/release`),
  releaseReport: (reportId: string) =>
    apiClient.post<Report>(`/doctor/reports/${reportId}/release`),
  reupload: (reportId: string, formData: FormData) =>
    apiClient.put<Report>(
      `/doctor/reports/${reportId}/reupload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  doctorReupload: (reportId: string, formData: FormData) =>
    apiClient.put<Report>(
      `/doctor/reports/${reportId}/reupload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  doctorVerifyField: (reportId: string, fieldName: string, body: FieldVerifyRequest) =>
    apiClient.post<FieldVerification>(
      `/doctor/reports/${reportId}/fields/${fieldName}/verify`,
      body,
    ),
  searchPatients: (query?: string, options?: RequestOptions) =>
    apiClient.get<PatientProfile[]>('/doctor/patients/search', {
      params: { query },
      signal: options?.signal,
    }),
  patientUpload: (formData: FormData) =>
    apiClient.post<UploadResponse>(
      '/patient/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  uploadReport: (formData: FormData) =>
    apiClient.post<UploadResponse>(
      '/patient/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  getMyReports: (params?: MyReportsParams) =>
    apiClient.get<Report[]>('/patient/reports/search', {
      params: {
        date_from: params?.date_from,
        date_to: params?.date_to,
        type: params?.document_type,
        lifecycle_status: params?.lifecycle_status,
        query: params?.query,
      },
    }),
  fetchMyReports: (params?: MyReportsParams) =>
    apiClient.get<Report[]>('/patient/reports/search', {
      params: {
        date_from: params?.date_from,
        date_to: params?.date_to,
        type: params?.document_type,
        lifecycle_status: params?.lifecycle_status,
        query: params?.query,
      },
    }),
  getMyReport: (reportId: string) =>
    apiClient.get<Report>(`/patient/reports/${reportId}`),
  fetchReportDetail: (reportId: string) =>
    apiClient.get<Report>(`/patient/reports/${reportId}`),
  getMyReportFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/patient/reports/${reportId}/fields`),
  fetchReportFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/patient/reports/${reportId}/fields`),
  fetchReportEda: (reportId: string) =>
    apiClient.get<ReportEdaResult>(`/patient/reports/${reportId}/eda`),
  patientReupload: (reportId: string, formData: FormData) =>
    apiClient.put<Report>(
      `/patient/reports/${reportId}/reupload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  reuploadReport: (reportId: string, formData: FormData) =>
    apiClient.put<Report>(
      `/patient/reports/${reportId}/reupload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  verifyField: (reportId: string, fieldName: string, body: FieldVerifyRequest) =>
    apiClient.post<FieldVerification>(
      `/patient/reports/${reportId}/fields/${fieldName}/verify`,
      body,
    ),
};
