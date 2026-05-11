import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { logout as apiLogout } from '../../api/auth';
import { Skeleton } from '../../components/ui/Skeleton';
import { useAuthStore } from '../../store/authStore';

export default function LogoutPage() {
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;

    async function logout() {
      try {
        await apiLogout();
      } catch {
        // Clear local auth state even if server logout fails.
      } finally {
        if (active) {
          clearAuth();
          navigate('/login', { replace: true });
        }
      }
    }

    void logout();

    return () => {
      active = false;
    };
  }, [clearAuth, navigate]);

  return <Skeleton variant="card" rows={3} />;
}
