import { useMutation, useQueryClient } from '@tanstack/react-query';
import { verificationApi } from '../api/verification';
import { normalizeApiError } from '../lib/apiError';
import { queryKeys } from '../lib/queryKeys';
import type { ApiError } from '../lib/apiError';
import type { FieldVerifyRequest, ReportField } from '../types/report';
import type { FieldVerification } from '../types/verification';

type VerifyVariables = {
  reportId: string;
  fieldName: string;
  data: FieldVerifyRequest;
};

type VerificationContext = {
  previousFields?: ReportField[];
};

function updateVerifiedField(
  fields: ReportField[] | undefined,
  fieldName: string,
  role: 'doctor' | 'patient',
): ReportField[] | undefined {
  return fields?.map((field) => {
    if (field.field_name !== fieldName) {
      return field;
    }

    return role === 'doctor'
      ? { ...field, doctor_verified: true, is_final: true }
      : { ...field, patient_verified: true };
  });
}

export function useVerifyField() {
  const queryClient = useQueryClient();

  return useMutation<FieldVerification, ApiError, VerifyVariables, VerificationContext>({
    mutationFn: async ({ reportId, fieldName, data }) => {
      try {
        const response = await verificationApi.verifyField(reportId, fieldName, data);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onMutate: async ({ reportId, fieldName }) => {
      const queryKey = queryKeys.reports.fields(reportId);
      await queryClient.cancelQueries({ queryKey });
      const previousFields = queryClient.getQueryData<ReportField[]>(queryKey);
      queryClient.setQueryData<ReportField[]>(
        queryKey,
        (fields) => updateVerifiedField(fields, fieldName, 'doctor') ?? [],
      );
      return { previousFields };
    },
    onError: (_error, variables, context) => {
      queryClient.setQueryData(
        queryKeys.reports.fields(variables.reportId),
        context?.previousFields,
      );
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.fields(variables.reportId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(variables.reportId) });
    },
  });
}

export function usePatientVerifyField() {
  const queryClient = useQueryClient();

  return useMutation<FieldVerification, ApiError, VerifyVariables, VerificationContext>({
    mutationFn: async ({ reportId, fieldName, data }) => {
      try {
        const response = await verificationApi.patientVerifyField(reportId, fieldName, data);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onMutate: async ({ reportId, fieldName }) => {
      const queryKey = queryKeys.reports.fields(reportId);
      await queryClient.cancelQueries({ queryKey });
      const previousFields = queryClient.getQueryData<ReportField[]>(queryKey);
      queryClient.setQueryData<ReportField[]>(
        queryKey,
        (fields) => updateVerifiedField(fields, fieldName, 'patient') ?? [],
      );
      return { previousFields };
    },
    onError: (_error, variables, context) => {
      queryClient.setQueryData(
        queryKeys.reports.fields(variables.reportId),
        context?.previousFields,
      );
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.fields(variables.reportId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(variables.reportId) });
    },
  });
}
