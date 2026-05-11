import { useNavigate } from 'react-router-dom';
import { logout as apiLogout } from '../../api/auth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { useAuthStore } from '../../store/authStore';

export default function VerificationPendingPage() {
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const navigate = useNavigate();
  const status = user?.verification_status ?? 'pending_verification';

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch {
      // Clear local auth state even if the server-side logout request fails.
    } finally {
      clearAuth();
      navigate('/login', { replace: true });
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-clinical-bg px-4 py-10">
      <Card className="w-full max-w-xl">
        <p className="text-sm font-medium text-clinical-primary">Doctor verification</p>
        <h1 className="mt-2 text-xl font-semibold text-clinical-text-primary">
          Your doctor account has been created successfully.
        </h1>
        <p className="mt-3 text-sm text-clinical-text-secondary">
          Access to clinical features will be enabled after admin verification.
        </p>
        <div className="mt-5 rounded-md border border-clinical-border bg-slate-50 px-4 py-3 text-sm">
          <p className="font-medium text-clinical-text-primary">
            Status: <span className="capitalize">{status.replaceAll('_', ' ')}</span>
          </p>
          {status === 'rejected' ? (
            <p className="mt-2 text-clinical-critical">
              {user?.verification_rejection_reason ?? 'Your verification was rejected. Please contact support.'}
            </p>
          ) : (
            <p className="mt-2 text-clinical-text-secondary">
              Admin review is required before you can access patient reports, HITL verification, analytics, and release workflows.
            </p>
          )}
        </div>
        <p className="mt-4 text-sm text-clinical-text-secondary">
          For urgent access or correction requests, contact your HDMIS administrator or support desk.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => navigate('/login', { replace: true })}>
            Back to login
          </Button>
          <Button variant="danger" onClick={() => void handleLogout()}>
            Logout
          </Button>
        </div>
      </Card>
    </main>
  );
}
