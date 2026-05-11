import { EmptyState } from '../../components/ui/EmptyState';

export default function UsersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Users</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Review user accounts and account access.</p>
      </div>

      {/* TODO: restore user management when verified admin backend routes are exposed. */}
      <EmptyState title="User management is not exposed by the current backend routes" />
    </div>
  );
}
