import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;

export default function DoctorsPage() {
  const [page, setPage] = useState(1);
  const filters = { page, page_size: pageSize };
  const doctors = useQuery({
    queryKey: queryKeys.admin.doctors(filters),
    queryFn: async () => (await adminApi.getDoctors(filters)).data,
    staleTime: staleTime.usersList,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Doctors" description="Doctor accounts and professional identifiers." />
      <QueryState
        isLoading={doctors.isLoading}
        isError={doctors.isError}
        error={doctors.error}
        onRetry={() => void doctors.refetch()}
        isEmpty={(doctors.data?.items ?? []).length === 0}
        emptyTitle="No doctors found"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>License</TableHead>
              <TableHead>Specialization</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(doctors.data?.items ?? []).map((doctor) => (
              <TableRow key={doctor.user_id}>
                <TableCell className="font-medium">{doctor.full_name}</TableCell>
                <TableCell>{doctor.email}</TableCell>
                <TableCell>{doctor.license_number ?? '-'}</TableCell>
                <TableCell>{doctor.specialization ?? '-'}</TableCell>
                <TableCell>{doctor.is_active ? 'Active' : 'Inactive'}</TableCell>
                <TableCell>{formatDate(doctor.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={doctors.data?.page ?? page} totalPages={doctors.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
