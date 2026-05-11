import { EmptyState } from '../../components/ui/EmptyState';

export default function AdminDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Admin Dashboard</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">System health and account activity.</p>
      </div>

      {/* TODO: restore admin dashboard data when verified admin backend routes are exposed. */}
      <EmptyState title="Admin dashboard data is not exposed by the current backend routes" />
    </div>
  );
}
