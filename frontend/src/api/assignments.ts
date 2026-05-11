import { apiClient } from './client';
import type {
  Assignment,
  DoctorAssignmentInviteRequest,
  PatientAssignmentRequest,
} from '../types/assignment';

export const assignmentsApi = {
  createAssignment: (data: DoctorAssignmentInviteRequest) =>
    apiClient.post<Assignment>('/doctor/assignments', data),
  invitePatient: (patientUid: string) =>
    apiClient.post<Assignment>('/doctor/assignments', { patient_uid: patientUid }),
  getDoctorAssignments: () =>
    apiClient.get<Assignment[]>('/doctor/assignments'),
  fetchDoctorAssignments: () =>
    apiClient.get<Assignment[]>('/doctor/assignments'),
  approveAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/doctor/assignments/${assignmentId}/approve`),
  rejectAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/doctor/assignments/${assignmentId}/reject`),
  createPatientAssignment: (data: PatientAssignmentRequest) =>
    apiClient.post<Assignment>('/patient/assignments', data),
  requestAssignment: (doctorId: string) =>
    apiClient.post<Assignment>('/patient/assignments', { doctor_id: doctorId }),
  getPatientAssignments: () =>
    apiClient.get<Assignment[]>('/patient/assignments'),
  fetchMyAssignments: () =>
    apiClient.get<Assignment[]>('/patient/assignments'),
  patientApproveAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/patient/assignments/${assignmentId}/approve`),
  patientRejectAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/patient/assignments/${assignmentId}/reject`),
};
