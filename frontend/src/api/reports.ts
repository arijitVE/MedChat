import type { AxiosRequestConfig } from 'axios';
import { apiClient } from './client';
import type {
  DoctorDashboard,
  DoctorHITLQueueItem,
  Report,
  ReportField,
} from '../types/report';
import type { PatientProfile } from '../types/assignment';

type RequestOptions = Pick<AxiosRequestConfig, 'signal'>;
type MyReportsParams = {
  date_from?: string;
  date_to?: string;
  document_type?: string;
};

export const reportsApi = {
  upload: (formData: FormData, force?: boolean) =>
    apiClient.post<Report>(
      `/doctor/upload${force ? '?force=true' : ''}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  getReport: (reportId: string) =>
    apiClient.get<Report>(`/doctor/reports/${reportId}`),
  getReportFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/doctor/reports/${reportId}/fields`),
  getRawFile: (reportId: string, options?: RequestOptions) =>
    apiClient.get<Blob>(`/doctor/reports/${reportId}/raw-file`, {
      responseType: 'blob',
      signal: options?.signal,
    }),
  releaseToPatient: (reportId: string) =>
    apiClient.post<Report>(`/doctor/reports/${reportId}/release`),
  reupload: (reportId: string, formData: FormData, force?: boolean) =>
    apiClient.put<Report>(
      `/doctor/reports/${reportId}/reupload${force ? '?force=true' : ''}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  getDoctorPatientReports: (patientId: string) =>
    apiClient.get<Report[]>(`/doctor/patients/${patientId}/reports`),
  getDashboard: () =>
    apiClient.get<DoctorDashboard>('/doctor/dashboard'),
  searchPatients: (q: string, options?: RequestOptions) =>
    apiClient.get<PatientProfile[]>('/doctor/patients/search', {
      params: { q },
      signal: options?.signal,
    }),
  getHITLQueue: (myPatientsOnly?: boolean) =>
    apiClient.get<DoctorHITLQueueItem[]>('/doctor/hitl-queue', {
      params: { my_patients_only: myPatientsOnly },
    }),
  patientUpload: (formData: FormData, force?: boolean) =>
    apiClient.post<Report>(
      `/patient/upload${force ? '?force=true' : ''}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
  getMyReports: (params?: MyReportsParams) =>
    apiClient.get<Report[]>('/patient/reports', { params }),
  getMyReport: (reportId: string) =>
    apiClient.get<Report>(`/patient/reports/${reportId}`),
  getMyReportFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/patient/reports/${reportId}/fields`),
  getMyReportRawFile: (reportId: string, options?: RequestOptions) =>
    apiClient.get<Blob>(`/patient/reports/${reportId}/raw-file`, {
      responseType: 'blob',
      signal: options?.signal,
    }),
  patientReupload: (reportId: string, formData: FormData, force?: boolean) =>
    apiClient.put<Report>(
      `/patient/reports/${reportId}/reupload${force ? '?force=true' : ''}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    ),
};
