import axios, { isAxiosError } from 'axios';
import { normalizeApiError } from '../lib/apiError';
import { useAuthStore } from '../store/authStore';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (isAxiosError(error) && error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(normalizeApiError(error));
  },
);

// P13: Production upgrade - when refresh token is implemented,
// add silent refresh logic here BEFORE the 401 redirect.
// See Section 19 for the full refresh token upgrade path.
