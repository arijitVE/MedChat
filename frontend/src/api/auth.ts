import { apiClient } from './client';
import type { BackendTokenResponse, LoginRequest, SignupRequest } from '../types/auth';

export const authApi = {
  signup: (data: SignupRequest) =>
    apiClient.post<BackendTokenResponse>('/auth/signup', data),
  login: (data: LoginRequest) =>
    apiClient.post<BackendTokenResponse>('/auth/login', data),
  logout: () =>
    apiClient.post<void>('/auth/logout'),
  refresh: () =>
    apiClient.post<BackendTokenResponse>('/auth/refresh'),
};
