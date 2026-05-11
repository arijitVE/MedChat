import { useMutation, useQuery } from '@tanstack/react-query';
import { intelligenceApi } from '../api/intelligence';
import { normalizeApiError } from '../lib/apiError';
import { queryKeys, staleTime } from '../lib/queryKeys';
import type { ApiError } from '../lib/apiError';
import type {
  DoctorQueryRequest,
  DoctorQueryResponse,
  PatientChatRequest,
  PatientChatResult,
} from '../types/intelligence';

type DoctorQueryVariables = {
  data: DoctorQueryRequest;
  signal?: AbortSignal;
};

type PatientChatVariables = {
  data: PatientChatRequest;
  signal?: AbortSignal;
};

export function useTrend(patientId: string, fieldName: string) {
  return useQuery({
    queryKey: queryKeys.patients.trend(patientId, fieldName),
    queryFn: async ({ signal }) => {
      try {
        const response = await intelligenceApi.getTrend(patientId, fieldName, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(patientId) && Boolean(fieldName),
    staleTime: staleTime.trends,
  });
}

export function useAnalytics(patientId: string) {
  return useQuery({
    queryKey: queryKeys.patients.analytics(patientId),
    queryFn: async ({ signal }) => {
      try {
        const response = await intelligenceApi.getAnalytics(patientId, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(patientId),
    staleTime: staleTime.analytics,
  });
}

export function useMyTrends(fieldName: string) {
  return useQuery({
    queryKey: queryKeys.patients.trend('me', fieldName),
    queryFn: async ({ signal }) => {
      try {
        const response = await intelligenceApi.getMyTrends(fieldName, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(fieldName),
    staleTime: staleTime.trends,
  });
}

export function useMyEDA(reportId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.reports.eda(reportId),
    queryFn: async ({ signal }) => {
      try {
        const response = await intelligenceApi.getMyEDA(reportId, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId) && enabled,
    staleTime: staleTime.analytics,
  });
}

export function useDoctorQuery() {
  return useMutation<DoctorQueryResponse, ApiError, DoctorQueryVariables>({
    mutationFn: async ({ data, signal }) => {
      try {
        const response = await intelligenceApi.doctorQuery(data, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
  });
}

export function usePatientChat() {
  return useMutation<PatientChatResult, ApiError, PatientChatVariables>({
    mutationFn: async ({ data, signal }) => {
      try {
        const response = await intelligenceApi.patientChat(data, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
  });
}
