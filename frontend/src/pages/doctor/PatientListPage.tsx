import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { EmptyState } from '../../components/ui/EmptyState';
import { Pagination } from '../../components/ui/Pagination';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import {
  useApproveAssignment,
  useCreateAssignment,
  useDoctorAssignments,
  useDoctorPatients,
  useRejectAssignment,
} from '../../hooks/useAssignments';
import { useAuth } from '../../hooks/useAuth';
import { usePatientSearch } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import type { PatientProfile } from '../../types/assignment';

function PatientRows({
  patients,
  assignmentStatusByPatient,
}: {
  patients: PatientProfile[];
  assignmentStatusByPatient: Map<string, string>;
}) {
  return (
    <>
      {patients.map((patient) => (
        <tr key={patient.user_id}>
          <td className="px-4 py-3">
            <Link className="font-medium text-clinical-primary hover:underline" to={`/doctor/patients/${patient.user_id}`}>
              {patient.full_name}
            </Link>
          </td>
          <td className="px-4 py-3 text-clinical-text-secondary">{patient.patient_uid}</td>
          <td className="px-4 py-3 text-clinical-text-secondary">{patient.email}</td>
          <td className="px-4 py-3 text-clinical-text-secondary">{patient.sex ?? '-'}</td>
          <td className="px-4 py-3 text-clinical-text-secondary">
            {assignmentStatusByPatient.get(patient.user_id) ?? 'unassigned'}
          </td>
        </tr>
      ))}
    </>
  );
}

export default function PatientListPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [patientId, setPatientId] = useState('');
  const patients = useDoctorPatients({ page, page_size: 20 });
  const searchResults = usePatientSearch(search);
  const assignments = useDoctorAssignments();
  const createAssignment = useCreateAssignment();
  const approveAssignment = useApproveAssignment();
  const rejectAssignment = useRejectAssignment();

  const visiblePatients = search.trim() ? searchResults.data ?? [] : patients.data?.items ?? [];
  const isLoading = search.trim() ? searchResults.isLoading : patients.isLoading;
  const isError = search.trim() ? searchResults.isError : patients.isError;
  const refetch = search.trim() ? searchResults.refetch : patients.refetch;
  const error = search.trim() ? searchResults.error : patients.error;

  const assignmentStatusByPatient = useMemo(() => {
    return new Map((assignments.data ?? []).map((assignment) => [assignment.patient_id, assignment.status]));
  }, [assignments.data]);

  if (isError) {
    return <RetryPanel onRetry={() => void refetch()} message={normalizeApiError(error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Patients</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Search and manage doctor-patient assignments.</p>
      </div>

      <Card>
        <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name or Patient UID"
            className="rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            aria-label="Search patients"
          />
          <input
            value={patientId}
            onChange={(event) => setPatientId(event.target.value)}
            placeholder="Patient ID"
            className="rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            aria-label="Patient ID for assignment"
          />
          <Button
            loading={createAssignment.isPending}
            disabled={!patientId || !user}
            onClick={() => {
              if (user) {
                createAssignment.mutate({ doctor_id: user.user_id, patient_id: patientId });
              }
            }}
          >
            Add Patient
          </Button>
        </div>
      </Card>

      <Card>
        {isLoading ? (
          <Skeleton variant="table-row" rows={8} />
        ) : visiblePatients.length === 0 ? (
          <EmptyState title="No patients found" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-clinical-text-secondary">
                <tr>
                  <th scope="col" className="px-4 py-3">Name</th>
                  <th scope="col" className="px-4 py-3">Patient UID</th>
                  <th scope="col" className="px-4 py-3">Email</th>
                  <th scope="col" className="px-4 py-3">Sex</th>
                  <th scope="col" className="px-4 py-3">Assignment Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-clinical-border">
                <PatientRows patients={visiblePatients} assignmentStatusByPatient={assignmentStatusByPatient} />
              </tbody>
            </table>
          </div>
        )}
        {!search.trim() && patients.data ? (
          <Pagination
            className="mt-4"
            page={patients.data.page}
            totalPages={patients.data.total_pages}
            onPageChange={setPage}
          />
        ) : null}
      </Card>

      <Card>
        <h2 className="mb-4 text-base font-semibold text-clinical-text-primary">Pending Assignments</h2>
        {assignments.isLoading ? (
          <Skeleton variant="table-row" rows={4} />
        ) : (
          <div className="space-y-2">
            {(assignments.data ?? []).filter((assignment) => assignment.status === 'pending').map((assignment) => (
              <div key={assignment.assignment_id} className="flex items-center justify-between rounded-md border border-clinical-border p-3">
                <span className="text-sm text-clinical-text-secondary">{assignment.patient_id}</span>
                <div className="flex gap-2">
                  <Button className="min-h-8 px-3 py-1" onClick={() => approveAssignment.mutate({ assignmentId: assignment.assignment_id })}>
                    Approve
                  </Button>
                  <Button className="min-h-8 px-3 py-1" variant="secondary" onClick={() => rejectAssignment.mutate({ assignmentId: assignment.assignment_id })}>
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
