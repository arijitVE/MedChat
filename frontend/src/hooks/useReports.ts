import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { reportsApi } from '../api/reports';
import { normalizeApiError } from '../lib/apiError';
import { queryKeys, staleTime } from '../lib/queryKeys';
import type { ApiError } from '../lib/apiError';
import type { Report, UploadResponse } from '../types/report';

type UploadVariables = {
  formData: FormData;
  force?: boolean;
};

type ReuploadVariables = UploadVariables & {
  reportId: string;
};

type MyReportsFilters = {
  date_from?: string;
  date_to?: string;
  document_type?: string;
  lifecycle_status?: string;
  query?: string;
};

function isReportProcessing(report: Report): boolean {
  return report.lifecycle_status === 'processing' || report.lifecycle_status === 'uploaded';
}

export function useReportDetail(reportId: string) {
  return useQuery({
    queryKey: queryKeys.reports.detail(reportId),
    queryFn: async () => {
      try {
        const response = await reportsApi.getReport(reportId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId),
    staleTime: staleTime.reportDetail,
    refetchInterval: (query) => {
      const status = query.state.data?.lifecycle_status;
      return status === 'processing' || status === 'uploaded' ? 8000 : false;
    },
  });
}

export function useReportFields(reportId: string) {
  return useQuery({
    queryKey: queryKeys.reports.fields(reportId),
    queryFn: async () => {
      try {
        const response = await reportsApi.getReportFields(reportId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId),
    staleTime: staleTime.reportFields,
  });
}

export function usePatientSearch(query: string) {
  return useQuery({
    queryKey: queryKeys.patients.search(query),
    queryFn: async ({ signal }) => {
      try {
        const response = await reportsApi.searchPatients(query, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: query.trim().length > 0,
    staleTime: staleTime.patientList,
  });
}

export function useMyReports(filters?: MyReportsFilters) {
  return useQuery({
    queryKey: queryKeys.reports.list(filters),
    queryFn: async () => {
      try {
        const response = await reportsApi.getMyReports(filters);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.reportDetail,
    refetchInterval: (query) => {
      const reports = query.state.data ?? [];
      return reports.some(isReportProcessing) ? 10000 : false;
    },
  });
}

export function useMyReport(reportId: string) {
  return useQuery({
    queryKey: queryKeys.reports.detail(reportId),
    queryFn: async () => {
      try {
        const response = await reportsApi.getMyReport(reportId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId),
    staleTime: staleTime.reportDetail,
    refetchInterval: (query) => {
      const status = query.state.data?.lifecycle_status;
      return status === 'processing' || status === 'uploaded' ? 8000 : false;
    },
  });
}

export function useMyReportFields(reportId: string) {
  return useQuery({
    queryKey: queryKeys.reports.fields(reportId),
    queryFn: async () => {
      try {
        const response = await reportsApi.getMyReportFields(reportId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId),
    staleTime: staleTime.reportFields,
  });
}

export function useUploadReport() {
  const queryClient = useQueryClient();

  return useMutation<Report, ApiError, UploadVariables>({
    mutationFn: async ({ formData }) => {
      try {
        const response = await reportsApi.upload(formData);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });
}

export function usePatientUploadReport() {
  const queryClient = useQueryClient();

  return useMutation<UploadResponse, ApiError, FormData>({
    mutationFn: (formData: FormData) => {
      try {
        return reportsApi.patientUpload(formData).then((response) => response.data);
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });
}

export function useReleaseToPatient() {
  const queryClient = useQueryClient();

  return useMutation<Report, ApiError, string>({
    mutationFn: async (reportId) => {
      try {
        const response = await reportsApi.releaseToPatient(reportId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });
}

export function useReuploadReport() {
  const queryClient = useQueryClient();

  return useMutation<Report, ApiError, ReuploadVariables>({
    mutationFn: async ({ reportId, formData }) => {
      try {
        const response = await reportsApi.reupload(reportId, formData);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.fields(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.eda(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });
}

export function usePatientReuploadReport() {
  const queryClient = useQueryClient();

  return useMutation<Report, ApiError, ReuploadVariables>({
    mutationFn: async ({ reportId, formData }) => {
      try {
        const response = await reportsApi.patientReupload(reportId, formData);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.fields(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.eda(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });
}
