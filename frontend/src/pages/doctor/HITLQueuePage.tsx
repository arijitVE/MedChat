import { EmptyState } from '../../components/ui/EmptyState';

export default function HITLQueuePage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-clinical-text-primary">HITL Queue</h1>
          <p className="mt-1 text-sm text-clinical-text-secondary">Reports that need doctor verification.</p>
        </div>
      </div>

      {/* TODO: restore queue data when the backend exposes a doctor HITL queue route. */}
      <EmptyState title="The current backend routes do not expose a doctor HITL queue" />
    </div>
  );
}
