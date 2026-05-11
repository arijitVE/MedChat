import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/admin';
import { Pagination } from '../../components/ui/Pagination';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/Table';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { PageHeader, QueryState } from './AdminUtils';
import { formatDate } from './adminFormat';

const pageSize = 20;

export default function FailedJobsPage() {
  const [page, setPage] = useState(1);
  const filters = { page, page_size: pageSize };
  const jobs = useQuery({
    queryKey: queryKeys.admin.failedJobs(filters),
    queryFn: async () => (await adminApi.getFailedJobs(filters)).data,
    staleTime: staleTime.hitlQueue,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Failed Jobs" description="Pipeline jobs and reports that ended in a failed state." />
      <QueryState
        isLoading={jobs.isLoading}
        isError={jobs.isError}
        error={jobs.error}
        onRetry={() => void jobs.refetch()}
        isEmpty={(jobs.data?.items ?? []).length === 0}
        emptyTitle="No failed jobs found"
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Job</TableHead>
              <TableHead>File</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Report Status</TableHead>
              <TableHead>Error</TableHead>
              <TableHead>Processed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(jobs.data?.items ?? []).map((job) => (
              <TableRow key={job.job_id}>
                <TableCell className="font-mono text-xs">{job.job_id}</TableCell>
                <TableCell>{job.file_name ?? '-'}</TableCell>
                <TableCell>{job.status}</TableCell>
                <TableCell>{job.lifecycle_status ?? '-'}</TableCell>
                <TableCell className="max-w-md truncate">{job.error_message ?? '-'}</TableCell>
                <TableCell>{formatDate(job.processed_at ?? job.uploaded_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </QueryState>
      <Pagination page={jobs.data?.page ?? page} totalPages={jobs.data?.total_pages ?? 1} onPageChange={setPage} />
    </div>
  );
}
