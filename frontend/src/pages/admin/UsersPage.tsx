import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Power, PowerOff } from 'lucide-react';
import { adminApi } from '../../api/admin';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Modal } from '../../components/ui/Modal';
import { Pagination } from '../../components/ui/Pagination';
import { Skeleton } from '../../components/ui/Skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/Table';
import { Toast } from '../../components/ui/Toast';
import { normalizeApiError } from '../../lib/apiError';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import type { ApiError } from '../../lib/apiError';
import type { UserListItem } from '../../types/admin';
import type { PaginatedResponse } from '../../types/common';

const pageSize = 20;
const roles = [
  { label: 'All', value: undefined },
  { label: 'Doctors', value: 'doctor' },
  { label: 'Patients', value: 'patient' },
] as const;

type RoleFilter = (typeof roles)[number]['value'];
type UserActionVariables = {
  userId: string;
  nextActive: boolean;
};
type UserActionContext = {
  previousUsers?: PaginatedResponse<UserListItem>;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

function ResetPasswordModal({
  user,
  isSubmitting,
  onClose,
  onSubmit,
}: {
  user: UserListItem | null;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (password: string) => void;
}) {
  const [password, setPassword] = useState('');

  return (
    <Modal
      isOpen={Boolean(user)}
      title="Reset password"
      onClose={() => {
        setPassword('');
        onClose();
      }}
    >
      {user ? (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit(password);
            setPassword('');
          }}
        >
          <p className="text-sm text-clinical-text-secondary">
            Set a new password for {user.full_name}.
          </p>
          <label className="block text-sm font-medium text-clinical-text-primary" htmlFor="new-password">
            New password
          </label>
          <input
            id="new-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded-md border border-clinical-border px-3 py-2 text-sm focus:border-clinical-primary focus:outline-none focus:ring-2 focus:ring-clinical-primary/20"
            required
            minLength={8}
          />
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={isSubmitting} disabled={password.length < 8}>
              Reset
            </Button>
          </div>
        </form>
      ) : null}
    </Modal>
  );
}

export default function UsersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [role, setRole] = useState<RoleFilter>(undefined);
  const [resetUser, setResetUser] = useState<UserListItem | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const filters = useMemo(() => ({ page, page_size: pageSize, role }), [page, role]);
  const queryKey = queryKeys.admin.users(filters);

  const users = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        const response = await adminApi.getUsers(filters);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    staleTime: staleTime.usersList,
  });

  const toggleActive = useMutation<UserListItem, ApiError, UserActionVariables, UserActionContext>({
    mutationFn: async ({ userId, nextActive }) => {
      try {
        const response = nextActive
          ? await adminApi.activateUser(userId)
          : await adminApi.deactivateUser(userId);
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onMutate: async ({ userId, nextActive }) => {
      await queryClient.cancelQueries({ queryKey });
      const previousUsers = queryClient.getQueryData<PaginatedResponse<UserListItem>>(queryKey);
      queryClient.setQueryData<PaginatedResponse<UserListItem>>(queryKey, (current) =>
        current
          ? {
              ...current,
              items: current.items.map((user) =>
                user.user_id === userId ? { ...user, is_active: nextActive } : user,
              ),
            }
          : current,
      );
      return { previousUsers };
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previousUsers);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const resetPassword = useMutation<void, ApiError, { userId: string; newPassword: string }>({
    mutationFn: async ({ userId, newPassword }) => {
      try {
        await adminApi.resetPassword({ user_id: userId, new_password: newPassword });
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    onSuccess: () => {
      setResetUser(null);
      setMessage('Password reset complete.');
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.usersAll });
    },
    onError: (error) => setMessage(normalizeApiError(error).message),
  });

  if (users.isError) {
    return <RetryPanel onRetry={() => void users.refetch()} message={normalizeApiError(users.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Users</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Review user accounts and account access.</p>
      </div>

      {message ? <Toast>{message}</Toast> : null}

      <Card className="p-4">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="User role filter">
          {roles.map((item) => (
            <button
              key={item.label}
              type="button"
              role="tab"
              aria-selected={role === item.value}
              className={`rounded-md px-3 py-2 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary ${
                role === item.value
                  ? 'bg-clinical-primary text-white'
                  : 'border border-clinical-border bg-clinical-surface text-clinical-text-secondary hover:bg-slate-50'
              }`}
              onClick={() => {
                setRole(item.value);
                setPage(1);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </Card>

      {users.isLoading ? (
        <Skeleton variant="table-row" rows={8} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Patient UID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(users.data?.items ?? []).map((user) => (
              <TableRow key={user.user_id}>
                <TableCell className="font-medium">{user.full_name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell className="capitalize">{user.role}</TableCell>
                <TableCell>{user.patient_uid ?? '-'}</TableCell>
                <TableCell>{user.is_active ? 'Active' : 'Inactive'}</TableCell>
                <TableCell>{formatDate(user.created_at)}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      className="min-h-8 px-3 py-1"
                      leftIcon={user.is_active ? <PowerOff className="h-4 w-4" aria-hidden="true" /> : <Power className="h-4 w-4" aria-hidden="true" />}
                      onClick={() => toggleActive.mutate({ userId: user.user_id, nextActive: !user.is_active })}
                    >
                      {user.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                    <Button
                      variant="secondary"
                      className="min-h-8 px-3 py-1"
                      leftIcon={<KeyRound className="h-4 w-4" aria-hidden="true" />}
                      onClick={() => setResetUser(user)}
                    >
                      Reset
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Pagination
        page={users.data?.page ?? page}
        totalPages={users.data?.total_pages ?? 1}
        onPageChange={setPage}
      />

      <ResetPasswordModal
        user={resetUser}
        isSubmitting={resetPassword.isPending}
        onClose={() => setResetUser(null)}
        onSubmit={(newPassword) => {
          if (resetUser) {
            resetPassword.mutate({ userId: resetUser.user_id, newPassword });
          }
        }}
      />
    </div>
  );
}
