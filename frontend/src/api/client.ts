import axios, { isAxiosError, type InternalAxiosRequestConfig } from 'axios';
import { normalizeApiError } from '../lib/apiError';
import { useAuthStore } from '../store/authStore';
import type { BackendTokenResponse, User } from '../types/auth';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type RefreshableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function saveRefreshToken(refreshToken?: string) {
  if (refreshToken) {
    localStorage.setItem('refresh_token', refreshToken);
  }
}

function buildRefreshedUser(response: BackendTokenResponse, currentUser: User | null): User | null {
  if (!currentUser) {
    return null;
  }

  return {
    ...currentUser,
    user_id: response.user_id,
    role: response.role,
  };
}

function redirectToLogin() {
  if (window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (isAxiosError(error) && error.response?.status === 401) {
      const originalRequest = error.config as RefreshableRequestConfig | undefined;
      const refreshToken = localStorage.getItem('refresh_token');
      const isRefreshRequest = originalRequest?.url?.endsWith('/auth/refresh') ?? false;

      if (!originalRequest || originalRequest._retry || isRefreshRequest || !refreshToken) {
        useAuthStore.getState().clearAuth();
        redirectToLogin();
        return Promise.reject(normalizeApiError(error));
      }

      originalRequest._retry = true;

      try {
        const refreshResponse = await axios.post<BackendTokenResponse>(
          `${BASE_URL}/auth/refresh`,
          { refresh_token: refreshToken },
        );
        const refreshedUser = buildRefreshedUser(refreshResponse.data, useAuthStore.getState().user);

        if (!refreshedUser) {
          useAuthStore.getState().clearAuth();
          redirectToLogin();
          return Promise.reject(normalizeApiError(error));
        }

        saveRefreshToken(refreshResponse.data.refresh_token);
        useAuthStore.getState().setAuth(refreshResponse.data.access_token, refreshedUser);
        originalRequest.headers.Authorization = `Bearer ${refreshResponse.data.access_token}`;

        return apiClient(originalRequest);
      } catch (refreshError) {
        useAuthStore.getState().clearAuth();
        redirectToLogin();
        return Promise.reject(normalizeApiError(refreshError));
      }
    }
    return Promise.reject(normalizeApiError(error));
  },
);
