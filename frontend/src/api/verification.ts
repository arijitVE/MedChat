import { apiClient } from './client';
import type { FieldEditRequest, FieldVerifyRequest, ReportVerificationResponse } from '../types/report';
import type { FieldVerification } from '../types/verification';

export const verificationApi = {
  verifyReport: (reportId: string) =>
    apiClient.post<ReportVerificationResponse>(`/doctor/reports/${reportId}/verify`),
  unlockReport: (reportId: string) =>
    apiClient.post<ReportVerificationResponse>(`/doctor/reports/${reportId}/unlock`),
  editField: (reportId: string, fieldName: string, data: FieldEditRequest) =>
    apiClient.post<FieldVerification>(
      `/doctor/reports/${reportId}/fields/${fieldName}/edit`,
      data,
    ),
  verifyField: (reportId: string, fieldName: string, data: FieldVerifyRequest) =>
    apiClient.post<FieldVerification>(
      `/doctor/reports/${reportId}/fields/${fieldName}/verify`,
      data,
    ),
  patientVerifyField: (reportId: string, fieldName: string, data: FieldVerifyRequest) =>
    apiClient.post<FieldVerification>(
      `/patient/reports/${reportId}/fields/${fieldName}/verify`,
      data,
    ),
};
