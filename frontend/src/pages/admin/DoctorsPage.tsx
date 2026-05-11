import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Button } from '../../components/ui/Button';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;

export default function DoctorsPage() {
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();
  const filters = { page, page_size: pageSize };
  const doctors = useQuery({
    queryKey: queryKeys.admin.doctors(filters),
    queryFn: async () => (await adminApi.getDoctors(filters)).data,
    staleTime: staleTime.usersList,
  });
  const verification = useMutation({
    mutationFn: async ({ doctorId, action }: { doctorId: string; action: 'approve' | 'reject' | 'suspend' }) => {
      if (action === 'approve') {
        return (await adminApi.approveDoctor(doctorId)).data;
      }
      if (action === 'suspend') {
        return (await adminApi.suspendDoctor(doctorId)).data;
      }
      return (await adminApi.rejectDoctor(doctorId, 'Rejected by administrator')).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.doctors(filters) });
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.usersAll });
    },
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
              <TableHead>Verification</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
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
                <TableCell>{doctor.verification_status?.replaceAll('_', ' ') ?? '-'}</TableCell>
                <TableCell>{formatDate(doctor.created_at)}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    {doctor.verification_status !== 'approved' ? (
                      <Button
                        className="min-h-8 px-3 py-1"
                        loading={verification.isPending}
                        onClick={() => verification.mutate({ doctorId: doctor.user_id, action: 'approve' })}
                      >
                        Approve
                      </Button>
                    ) : null}
                    {doctor.verification_status !== 'rejected' ? (
                      <Button
                        variant="secondary"
                        className="min-h-8 px-3 py-1"
                        loading={verification.isPending}
                        onClick={() => verification.mutate({ doctorId: doctor.user_id, action: 'reject' })}
                      >
                        Reject
                      </Button>
                    ) : null}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={doctors.data?.page ?? page} totalPages={doctors.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
