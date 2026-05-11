import { useState } from 'react';
import { Copy, LogOut, KeyRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { logout as apiLogout } from '../../api/auth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Toast } from '../../components/ui/Toast';
import { useAuthStore } from '../../store/authStore';
import type { User } from '../../types/auth';

type ProfileUser = User & {
  created_at?: string;
};

function formatMemberSince(createdAt?: string) {
  if (!createdAt) {
    return 'Not available';
  }

  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(createdAt));
}

export default function AccountPage() {
  const user = useAuthStore((state) => state.user) as ProfileUser | null;
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const patientUid = user?.patient_uid ?? user?.user_id ?? '';

  const handleCopy = async () => {
    if (!patientUid) {
      return;
    }

    try {
      await navigator.clipboard.writeText(patientUid);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setMessage('Unable to copy Patient ID');
    }
  };

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
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Account</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Manage your patient account details.</p>
      </div>

      {message ? <Toast>{message}</Toast> : null}

      {/* TODO: replace auth-store-only profile data with GET /users/me if that route is added. */}
      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Personal Information</h2>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-clinical-text-secondary">Full name</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{user?.full_name ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Email address</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{user?.email ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Role</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">Patient</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Member since</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{formatMemberSince(user?.created_at)}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Patient ID</h2>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1 rounded-md border border-blue-200 bg-blue-50 px-4 py-3">
            <p className="text-xs font-medium uppercase text-blue-800">Your Patient ID</p>
            <p className="mt-2 break-all font-mono text-base font-semibold text-blue-950">
              {patientUid || 'Not available'}
            </p>
          </div>
          <Button
            variant="secondary"
            leftIcon={<Copy className="h-4 w-4" aria-hidden="true" />}
            onClick={() => void handleCopy()}
            disabled={!patientUid}
          >
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        </div>
        <p className="mt-3 text-sm text-clinical-text-secondary">
          Share this ID with your doctor so they can link your account and access your reports.
        </p>
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Account Actions</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button
            variant="secondary"
            leftIcon={<KeyRound className="h-4 w-4" aria-hidden="true" />}
            onClick={() => setMessage('Password change coming soon')}
          >
            Change Password
          </Button>
          <Button
            variant="danger"
            leftIcon={<LogOut className="h-4 w-4" aria-hidden="true" />}
            onClick={() => void handleLogout()}
          >
            Logout
          </Button>
        </div>
      </Card>
    </div>
  );
}
