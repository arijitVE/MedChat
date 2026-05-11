import { apiClient } from './client';
import type { BackendTokenResponse, LoginRequest, RefreshTokenRequest, SignupRequest, User } from '../types/auth';

export const authApi = {
  signup: (data: SignupRequest) =>
    apiClient.post<BackendTokenResponse>('/auth/signup', data),
  login: (data: LoginRequest) =>
    apiClient.post<BackendTokenResponse>('/auth/login', data),
  logout: () =>
    apiClient.post<void>('/auth/logout'),
  refresh: (data: RefreshTokenRequest) =>
    apiClient.post<BackendTokenResponse>('/auth/refresh', data),
  me: () =>
    apiClient.get<User>('/users/me'),
};

export const logout = () => authApi.logout().then((response) => response.data);
export const fetchMyProfile = () => authApi.me().then((response) => response.data);
