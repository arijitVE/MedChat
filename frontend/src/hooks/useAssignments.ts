import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { assignmentsApi } from '../api/assignments';
import { normalizeApiError } from '../lib/apiError';
import { queryKeys, staleTime } from '../lib/queryKeys';
import type { ApiError } from '../lib/apiError';
import type {
  Assignment,
  AssignmentStatus,
  DoctorAssignmentInviteRequest,
  PatientAssignmentRequest,
} from '../types/assignment';

type AssignmentActionVariables = {
  assignmentId: string;
};

type AssignmentContext = {
  previousAssignments?: Assignment[];
};

function updateAssignmentStatus(
  assignments: Assignment[] | undefined,
  assignmentId: string,
  status: AssignmentStatus,
): Assignment[] | undefined {
  return assignments?.map((assignment) =>
    assignment.assignment_id === assignmentId ? { ...assignment, status } : assignment,
  );
}

function useAssignmentAction(
  role: 'doctor' | 'patient',
  status: AssignmentStatus,
  action: (assignmentId: string) => Promise<{ data: Assignment }>,
) {
  const queryClient = useQueryClient();
  const queryKey = role === 'doctor' ? queryKeys.assignments.doctor : queryKeys.assignments.patient;

  return useMutation<Assignment, ApiError, AssignmentActionVariables, AssignmentContext>({
    mutationFn: async ({ assignmentId }) => {
      try {
        const response = await action(assignmentId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onMutate: async ({ assignmentId }) => {
      await queryClient.cancelQueries({ queryKey });
      const previousAssignments = queryClient.getQueryData<Assignment[]>(queryKey);
      queryClient.setQueryData<Assignment[]>(
        queryKey,
        (assignments) => updateAssignmentStatus(assignments, assignmentId, status) ?? [],
      );
      return { previousAssignments };
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previousAssignments);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
      queryClient.invalidateQueries({ queryKey: queryKeys.patients.all });
    },
  });
}

export function useDoctorAssignments() {
  return useQuery({
    queryKey: queryKeys.assignments.doctor,
    queryFn: async () => {
      try {
        const response = await assignmentsApi.getDoctorAssignments();
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.patientList,
  });
}

export function usePatientAssignments() {
  return useQuery({
    queryKey: queryKeys.assignments.patient,
    queryFn: async () => {
      try {
        const response = await assignmentsApi.getPatientAssignments();
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.patientList,
  });
}

export function useCreateAssignment() {
  const queryClient = useQueryClient();

  return useMutation<Assignment, ApiError, DoctorAssignmentInviteRequest>({
    mutationFn: async (data) => {
      try {
        const response = await assignmentsApi.createAssignment(data);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.assignments.doctor });
      queryClient.invalidateQueries({ queryKey: queryKeys.patients.all });
    },
  });
}

export function useCreatePatientAssignment() {
  const queryClient = useQueryClient();

  return useMutation<Assignment, ApiError, PatientAssignmentRequest>({
    mutationFn: async (data) => {
      try {
        const response = await assignmentsApi.createPatientAssignment(data);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.assignments.patient });
    },
  });
}

export function useApproveAssignment() {
  return useAssignmentAction('doctor', 'active', assignmentsApi.approveAssignment);
}

export function useRejectAssignment() {
  return useAssignmentAction('doctor', 'rejected', assignmentsApi.rejectAssignment);
}

export function usePatientApproveAssignment() {
  return useAssignmentAction('patient', 'active', assignmentsApi.patientApproveAssignment);
}

export function usePatientRejectAssignment() {
  return useAssignmentAction('patient', 'rejected', assignmentsApi.patientRejectAssignment);
}
