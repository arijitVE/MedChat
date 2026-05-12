import type { AxiosRequestConfig } from 'axios';
import { apiClient } from './client';
import type {
  AnalyticsResult,
  DoctorQueryRequest,
  DoctorQueryResponse,
  PatientChatRequest,
  PatientChatResult,
  TrendResult,
} from '../types/intelligence';
import type { ReportEdaResult } from '../types/report';

type RequestOptions = Pick<AxiosRequestConfig, 'signal'>;

export const intelligenceApi = {
  doctorQuery: (data: DoctorQueryRequest, options?: RequestOptions) =>
    apiClient.post<DoctorQueryResponse>('/doctor/query', data, {
      signal: options?.signal,
    }),
  getTrend: (patientId: string, fieldName: string, options?: RequestOptions) =>
    apiClient.get<TrendResult>(`/doctor/patients/${patientId}/trend`, {
      params: { field_name: fieldName },
      signal: options?.signal,
    }),
  fetchPatientTrend: (patientId: string, fieldName: string, options?: RequestOptions) =>
    apiClient.get<TrendResult>(`/doctor/patients/${patientId}/trend`, {
      params: { field_name: fieldName },
      signal: options?.signal,
    }),
  getAnalytics: (patientId: string, options?: RequestOptions) =>
    apiClient.get<AnalyticsResult>(`/doctor/patients/${patientId}/analytics`, {
      signal: options?.signal,
    }),
  patientChat: (data: PatientChatRequest, options?: RequestOptions) =>
    apiClient.post<PatientChatResult>('/patient/chat', data, {
      signal: options?.signal,
    }),
  getMyTrends: (fieldName: string, options?: RequestOptions) =>
    apiClient.get<TrendResult>('/patient/trends', {
      params: { field_name: fieldName },
      signal: options?.signal,
    }),
  getMyAnalytics: (options?: RequestOptions) =>
    apiClient.get<AnalyticsResult>('/patient/analytics', {
      signal: options?.signal,
    }),
  fetchMyTrend: (fieldName: string, options?: RequestOptions) =>
    apiClient.get<TrendResult>('/patient/trends', {
      params: { field_name: fieldName },
      signal: options?.signal,
    }),
  getMyEDA: (reportId: string, options?: RequestOptions) =>
    apiClient.get<ReportEdaResult>(`/patient/reports/${reportId}/eda`, {
      signal: options?.signal,
    }),
};
