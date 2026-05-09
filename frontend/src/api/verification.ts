import { apiClient } from './client';
import type { FieldVerifyRequest } from '../types/report';
import type { FieldVerification } from '../types/verification';

export const verificationApi = {
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
