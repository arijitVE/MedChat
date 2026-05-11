import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { KeyRound, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchMyProfile, logout as apiLogout } from '../../api/auth';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Toast } from '../../components/ui/Toast';
import { useAuthStore } from '../../store/authStore';
import type { User } from '../../types/auth';

function formatDate(value?: string | null) {
  if (!value) {
    return 'Not available';
  }
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

export default function DoctorAccountPage() {
  const user = useAuthStore((state) => state.user);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const navigate = useNavigate();
  const [message, setMessage] = useState<string | null>(null);
  const profile = useQuery<User>({
    queryKey: ['users', 'me'],
    queryFn: fetchMyProfile,
    initialData: user ?? undefined,
  });
  const profileUser = profile.data ?? user;

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
        <h1 className="text-lg font-semibold text-clinical-text-primary">Account/Profile</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Manage your doctor account details.</p>
      </div>

      {message ? <Toast>{message}</Toast> : null}

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Personal Information</h2>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-clinical-text-secondary">Full name</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.full_name ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Email</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.email ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Phone</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.phone ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Address</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.address ?? 'Not available'}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Professional Information</h2>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-clinical-text-secondary">Specialization</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.specialization ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">License number</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.license_number ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Hospital</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.hospital_name ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Department</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.department ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Years of experience</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.years_of_experience ?? 'Not available'}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">System Information</h2>
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-clinical-text-secondary">Doctor ID</dt>
            <dd className="mt-1 break-all font-mono text-xs font-medium text-clinical-text-primary">{profileUser?.user_id ?? 'Not available'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Account status</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{profileUser?.account_status ?? 'Active'}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Verification status</dt>
            <dd className="mt-1 font-medium capitalize text-clinical-text-primary">
              {profileUser?.verification_status?.replaceAll('_', ' ') ?? 'Not available'}
            </dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Created</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{formatDate(profileUser?.created_at)}</dd>
          </div>
          <div>
            <dt className="text-clinical-text-secondary">Last login</dt>
            <dd className="mt-1 font-medium text-clinical-text-primary">{formatDate(profileUser?.last_login)}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Security</h2>
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
