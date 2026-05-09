import { apiClient } from './client';
import type { AdminStats, HITLQueueItem, PasswordResetRequest, UserListItem } from '../types/admin';
import {
  normalizePaginationParams,
  type PaginatedResponse,
  type PaginationParams,
} from '../types/common';

type UserListParams = PaginationParams & { role?: 'doctor' | 'patient' | 'admin' };

export const adminApi = {
  getStats: () =>
    apiClient.get<AdminStats>('/admin/stats'),
  getUsers: (params: UserListParams = {}) =>
    apiClient.get<PaginatedResponse<UserListItem>>('/admin/users', {
      params: { ...normalizePaginationParams(params), role: params.role },
    }),
  getUser: (userId: string) =>
    apiClient.get<UserListItem>(`/admin/users/${userId}`),
  getHITLQueue: () =>
    apiClient.get<HITLQueueItem[]>('/admin/hitl-queue'),
  resetPassword: (data: PasswordResetRequest) =>
    apiClient.post<void>('/admin/password-reset', data),
  deactivateUser: (userId: string) =>
    apiClient.put<UserListItem>(`/admin/users/${userId}/deactivate`),
  activateUser: (userId: string) =>
    apiClient.put<UserListItem>(`/admin/users/${userId}/activate`),
};
