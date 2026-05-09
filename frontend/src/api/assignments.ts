import { apiClient } from './client';
import type { Assignment, AssignmentRequest, PatientProfile } from '../types/assignment';
import {
  normalizePaginationParams,
  type PaginatedResponse,
  type PaginationParams,
} from '../types/common';

export const assignmentsApi = {
  createAssignment: (data: AssignmentRequest) =>
    apiClient.post<Assignment>('/doctor/assignments', data),
  getDoctorAssignments: () =>
    apiClient.get<Assignment[]>('/doctor/assignments'),
  approveAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/doctor/assignments/${assignmentId}/approve`),
  rejectAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/doctor/assignments/${assignmentId}/reject`),
  getDoctorPatients: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<PatientProfile>>('/doctor/patients', {
      params: normalizePaginationParams(params),
    }),
  getPatientProfile: (patientId: string) =>
    apiClient.get<PatientProfile>(`/doctor/patients/${patientId}/profile`),
  createPatientAssignment: (data: AssignmentRequest) =>
    apiClient.post<Assignment>('/patient/assignments', data),
  getPatientAssignments: () =>
    apiClient.get<Assignment[]>('/patient/assignments'),
  patientApproveAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/patient/assignments/${assignmentId}/approve`),
  patientRejectAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/patient/assignments/${assignmentId}/reject`),
  adminCreateAssignment: (data: AssignmentRequest) =>
    apiClient.post<Assignment>('/admin/assignments', data),
};
