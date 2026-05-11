import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;

export default function PatientsPage() {
  const [page, setPage] = useState(1);
  const filters = { page, page_size: pageSize };
  const patients = useQuery({
    queryKey: queryKeys.admin.patients(filters),
    queryFn: async () => (await adminApi.getPatients(filters)).data,
    staleTime: staleTime.usersList,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Patients" description="Patient accounts and patient IDs." />
      <QueryState
        isLoading={patients.isLoading}
        isError={patients.isError}
        error={patients.error}
        onRetry={() => void patients.refetch()}
        isEmpty={(patients.data?.items ?? []).length === 0}
        emptyTitle="No patients found"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Patient UID</TableHead>
              <TableHead>Sex</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(patients.data?.items ?? []).map((patient) => (
              <TableRow key={patient.user_id}>
                <TableCell className="font-medium">{patient.full_name}</TableCell>
                <TableCell>{patient.email}</TableCell>
                <TableCell>{patient.patient_uid ?? '-'}</TableCell>
                <TableCell>{patient.sex ?? '-'}</TableCell>
                <TableCell>{patient.is_active ? 'Active' : 'Inactive'}</TableCell>
                <TableCell>{formatDate(patient.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={patients.data?.page ?? page} totalPages={patients.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
