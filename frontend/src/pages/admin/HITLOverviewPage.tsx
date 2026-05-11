import { EmptyState } from '../../components/ui/EmptyState';

export default function HITLOverviewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">HITL Overview</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Read-only view of reports waiting for verification.</p>
      </div>

      {/* TODO: restore admin HITL overview when verified admin backend routes are exposed. */}
      <EmptyState title="Admin HITL data is not exposed by the current backend routes" />
    </div>
  );
}
