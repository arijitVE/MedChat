import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { reportsApi } from '../api/reports';
import { normalizeApiError } from '../lib/apiError';
import { queryKeys, staleTime } from '../lib/queryKeys';
import type { ApiError } from '../lib/apiError';
import type { Report } from '../types/report';

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
};

export function useDoctorDashboard() {
  return useQuery({
    queryKey: queryKeys.doctor.dashboard,
    queryFn: async () => {
      try {
        const response = await reportsApi.getDashboard();
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.reportDetail,
  });
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

export function useReportRawFile(reportId: string) {
  return useQuery({
    queryKey: queryKeys.reports.rawFile(reportId),
    queryFn: async ({ signal }) => {
      try {
        const response = await reportsApi.getRawFile(reportId, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId),
    staleTime: staleTime.reportDetail,
  });
}

export function useDoctorPatientReports(patientId: string) {
  return useQuery({
    queryKey: queryKeys.reports.forPatient(patientId),
    queryFn: async () => {
      try {
        const response = await reportsApi.getDoctorPatientReports(patientId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(patientId),
    staleTime: staleTime.reportDetail,
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

export function useDoctorHITLQueue(myPatientsOnly = false) {
  return useQuery({
    queryKey: queryKeys.hitlQueue(myPatientsOnly),
    queryFn: async () => {
      try {
        const response = await reportsApi.getHITLQueue(myPatientsOnly);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.hitlQueue,
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

export function useMyReportRawFile(reportId: string) {
  return useQuery({
    queryKey: queryKeys.reports.rawFile(reportId),
    queryFn: async ({ signal }) => {
      try {
        const response = await reportsApi.getMyReportRawFile(reportId, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId),
    staleTime: staleTime.reportDetail,
  });
}

export function useUploadReport() {
  const queryClient = useQueryClient();

  return useMutation<Report, ApiError, UploadVariables>({
    mutationFn: async ({ formData, force }) => {
      try {
        const response = await reportsApi.upload(formData, force);
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

  return useMutation<Report, ApiError, UploadVariables>({
    mutationFn: async ({ formData, force }) => {
      try {
        const response = await reportsApi.patientUpload(formData, force);
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
    mutationFn: async ({ reportId, formData, force }) => {
      try {
        const response = await reportsApi.reupload(reportId, formData, force);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.fields(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.rawFile(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.eda(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });
}

export function usePatientReuploadReport() {
  const queryClient = useQueryClient();

  return useMutation<Report, ApiError, ReuploadVariables>({
    mutationFn: async ({ reportId, formData, force }) => {
      try {
        const response = await reportsApi.patientReupload(reportId, formData, force);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.fields(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.rawFile(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.eda(report.report_id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });
}
