import { apiClient } from './client';
import type {
  AdminAnalytics,
  AdminAssignment,
  AdminNotificationItem,
  AdminStats,
  AuditLogItem,
  FailedJobItem,
  HITLQueueItem,
  PasswordResetRequest,
  SystemHealth,
  SystemSettings,
  UserListItem,
  AdminReportItem,
} from '../types/admin';
import {
  normalizePaginationParams,
  type PaginatedResponse,
  type PaginationParams,
} from '../types/common';

type UserListParams = PaginationParams & { role?: 'doctor' | 'patient' | 'admin' };
type ReportListParams = PaginationParams & { status?: string };

export const adminApi = {
  getStats: () =>
    apiClient.get<AdminStats>('/admin/stats'),
  getDashboard: () =>
    apiClient.get<AdminStats>('/admin/dashboard'),
  getUsers: (params: UserListParams = {}) =>
    apiClient.get<PaginatedResponse<UserListItem>>('/admin/users', {
      params: { ...normalizePaginationParams(params), role: params.role },
    }),
  getDoctors: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<UserListItem>>('/admin/doctors', {
      params: normalizePaginationParams(params),
    }),
  getPatients: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<UserListItem>>('/admin/patients', {
      params: normalizePaginationParams(params),
    }),
  getUser: (userId: string) =>
    apiClient.get<UserListItem>(`/admin/users/${userId}`),
  getAssignments: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<AdminAssignment>>('/admin/assignments', {
      params: normalizePaginationParams(params),
    }),
  createAssignment: (doctorId: string, patientId: string) =>
    apiClient.post<AdminAssignment>('/admin/assignments', {
      doctor_id: doctorId,
      patient_id: patientId,
    }),
  getReports: (params: ReportListParams = {}) =>
    apiClient.get<PaginatedResponse<AdminReportItem>>('/admin/reports', {
      params: { ...normalizePaginationParams(params), status: params.status },
    }),
  getFailedJobs: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<FailedJobItem>>('/admin/failed-jobs', {
      params: normalizePaginationParams(params),
    }),
  getHITLQueue: () =>
    apiClient.get<HITLQueueItem[]>('/admin/hitl-queue'),
  getAnalytics: () =>
    apiClient.get<AdminAnalytics>('/admin/analytics'),
  getNotifications: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<AdminNotificationItem>>('/admin/notifications', {
      params: normalizePaginationParams(params),
    }),
  getAuditLogs: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<AuditLogItem>>('/admin/audit-logs', {
      params: normalizePaginationParams(params),
    }),
  getSystemHealth: () =>
    apiClient.get<SystemHealth>('/admin/system-health'),
  getSettings: () =>
    apiClient.get<SystemSettings>('/admin/settings'),
  resetPassword: (data: PasswordResetRequest) =>
    apiClient.post<void>('/admin/password-reset', data),
  deactivateUser: (userId: string) =>
    apiClient.put<UserListItem>(`/admin/users/${userId}/deactivate`),
  activateUser: (userId: string) =>
    apiClient.put<UserListItem>(`/admin/users/${userId}/activate`),
};
