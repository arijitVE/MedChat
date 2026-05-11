import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { Toast } from '../../components/ui/Toast';
import { normalizeApiError } from '../../lib/apiError';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;

export default function AssignmentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [doctorId, setDoctorId] = useState('');
  const [patientId, setPatientId] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const filters = { page, page_size: pageSize };

  const assignments = useQuery({
    queryKey: queryKeys.admin.assignments(filters),
    queryFn: async () => (await adminApi.getAssignments(filters)).data,
    staleTime: staleTime.patientList,
  });
  const doctors = useQuery({
    queryKey: queryKeys.admin.doctors({ page: 1, page_size: 100 }),
    queryFn: async () => (await adminApi.getDoctors({ page: 1, page_size: 100 })).data,
    staleTime: staleTime.usersList,
  });
  const patients = useQuery({
    queryKey: queryKeys.admin.patients({ page: 1, page_size: 100 }),
    queryFn: async () => (await adminApi.getPatients({ page: 1, page_size: 100 })).data,
    staleTime: staleTime.usersList,
  });
  const canAssign = useMemo(() => Boolean(doctorId && patientId), [doctorId, patientId]);

  const createAssignment = useMutation({
    mutationFn: async () => (await adminApi.createAssignment(doctorId, patientId)).data,
    onSuccess: () => {
      setMessage('Doctor assigned to patient.');
      setDoctorId('');
      setPatientId('');
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.assignments() });
    },
    onError: (error) => setMessage(normalizeApiError(error).message),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Assign Doctor to Patient" description="Create and review doctor-patient assignments." />
      {message ? <Toast>{message}</Toast> : null}

      <Card>
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
          <select
            value={doctorId}
            onChange={(event) => setDoctorId(event.target.value)}
            className="rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            aria-label="Doctor"
          >
            <option value="">Select doctor</option>
            {(doctors.data?.items ?? []).map((doctor) => (
              <option key={doctor.user_id} value={doctor.user_id}>{doctor.full_name}</option>
            ))}
          </select>
          <select
            value={patientId}
            onChange={(event) => setPatientId(event.target.value)}
            className="rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            aria-label="Patient"
          >
            <option value="">Select patient</option>
            {(patients.data?.items ?? []).map((patient) => (
              <option key={patient.user_id} value={patient.user_id}>
                {patient.full_name} {patient.patient_uid ? `(${patient.patient_uid})` : ''}
              </option>
            ))}
          </select>
          <Button loading={createAssignment.isPending} disabled={!canAssign} onClick={() => createAssignment.mutate()}>
            Assign
          </Button>
        </div>
      </Card>

      <QueryState
        isLoading={assignments.isLoading}
        isError={assignments.isError}
        error={assignments.error}
        onRetry={() => void assignments.refetch()}
        isEmpty={(assignments.data?.items ?? []).length === 0}
        emptyTitle="No assignments found"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Doctor</TableHead>
              <TableHead>Patient</TableHead>
              <TableHead>Patient UID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Assigned By</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(assignments.data?.items ?? []).map((assignment) => (
              <TableRow key={assignment.assignment_id}>
                <TableCell>{assignment.doctor_name ?? assignment.doctor_id}</TableCell>
                <TableCell>{assignment.patient_name ?? assignment.patient_id}</TableCell>
                <TableCell>{assignment.patient_uid ?? '-'}</TableCell>
                <TableCell className="capitalize">{assignment.status}</TableCell>
                <TableCell className="capitalize">{assignment.assigned_by}</TableCell>
                <TableCell>{formatDate(assignment.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={assignments.data?.page ?? page} totalPages={assignments.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
