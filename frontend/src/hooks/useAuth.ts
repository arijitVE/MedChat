import { useMutation } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { normalizeApiError } from '../lib/apiError';
import { useAuthStore } from '../store/authStore';
import type { BackendTokenResponse, LoginRequest, SignupRequest, TokenResponse, User } from '../types/auth';
import type { ApiError } from '../lib/apiError';

export function useAuth() {
  return useAuthStore();
}

function normalizeSignupUser(response: BackendTokenResponse, data: SignupRequest): User {
  return {
    user_id: response.user_id,
    role: response.role,
    email: data.email,
    full_name: data.full_name,
    phone: data.phone_number ?? data.phone ?? undefined,
    age: data.age ?? undefined,
    gender: data.gender ?? data.sex ?? undefined,
    blood_group: data.blood_group ?? undefined,
    allergies: data.allergies ?? undefined,
    chronic_conditions: data.chronic_conditions ?? undefined,
    address: data.address ?? undefined,
    emergency_contact: data.emergency_contact ?? undefined,
    patient_uid: data.claim_patient_uid ?? undefined,
    license_number: data.license_number ?? undefined,
    specialization: data.specialization ?? undefined,
    hospital_name: data.hospital_name ?? undefined,
    years_of_experience: data.years_of_experience ?? undefined,
    department: data.department ?? undefined,
    profile_photo: data.profile_photo ?? undefined,
    verification_status: response.role === 'doctor' ? 'pending_verification' : 'approved',
  };
}

function normalizeLoginUser(response: BackendTokenResponse, data: LoginRequest, currentUser: User | null): User {
  const matchingUser = currentUser?.user_id === response.user_id ? currentUser : null;

  return {
    user_id: response.user_id,
    role: response.role,
    email: matchingUser?.email ?? data.email,
    full_name: matchingUser?.full_name ?? data.email,
    patient_uid: matchingUser?.patient_uid,
    license_number: matchingUser?.license_number,
    specialization: matchingUser?.specialization,
    hospital_name: matchingUser?.hospital_name,
    years_of_experience: matchingUser?.years_of_experience,
    department: matchingUser?.department,
    profile_photo: matchingUser?.profile_photo,
    verification_status: matchingUser?.verification_status,
  };
}

function normalizeTokenResponse(response: BackendTokenResponse, user: User): TokenResponse {
  return {
    access_token: response.access_token,
    token_type: response.token_type,
    user,
  };
}

function storeRefreshToken(refreshToken?: string) {
  if (refreshToken) {
    localStorage.setItem('refresh_token', refreshToken);
    return;
  }

  localStorage.removeItem('refresh_token');
}

export function useLogin() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation<TokenResponse, ApiError, LoginRequest>({
    mutationFn: async (data) => {
      try {
        const response = await authApi.login(data);
        const user = normalizeLoginUser(response.data, data, useAuthStore.getState().user);
        storeRefreshToken(response.data.refresh_token);
        setAuth(response.data.access_token, user);
        try {
          const profile = await authApi.me();
          setAuth(response.data.access_token, profile.data);
          return normalizeTokenResponse(response.data, profile.data);
        } catch {
          return normalizeTokenResponse(response.data, user);
        }
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
  });
}

export function useSignup() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation<TokenResponse, ApiError, SignupRequest>({
    mutationFn: async (data) => {
      try {
        const response = await authApi.signup(data);
        const user = normalizeSignupUser(response.data, data);
        storeRefreshToken(response.data.refresh_token);
        setAuth(response.data.access_token, user);
        try {
          const profile = await authApi.me();
          setAuth(response.data.access_token, profile.data);
          return normalizeTokenResponse(response.data, profile.data);
        } catch {
          return normalizeTokenResponse(response.data, user);
        }
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
  });
}

export function useLogout() {
  const logout = useAuthStore((state) => state.logout);

  return useMutation<void, ApiError>({
    mutationFn: async () => {
      try {
        await authApi.logout();
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSettled: () => {
      logout();
    },
  });
}
