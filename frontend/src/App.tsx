import { lazy, Suspense } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { NetworkDisconnectedBanner } from './components/feedback/NetworkDisconnectedBanner';
import { AppShell } from './components/layout/AppShell';
import { Skeleton } from './components/ui/Skeleton';
import LoginPage from './pages/auth/LoginPage';
import SignupPage from './pages/auth/SignupPage';
import { useAuthStore } from './store/authStore';
import type { User } from './types/auth';

const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const AdminAnalyticsPage = lazy(() => import('./pages/admin/AnalyticsPage'));
const AdminAssignmentsPage = lazy(() => import('./pages/admin/AssignmentsPage'));
const AdminAuditLogsPage = lazy(() => import('./pages/admin/AuditLogsPage'));
const AdminDoctorsPage = lazy(() => import('./pages/admin/DoctorsPage'));
const AdminFailedJobsPage = lazy(() => import('./pages/admin/FailedJobsPage'));
const HITLOverviewPage = lazy(() => import('./pages/admin/HITLOverviewPage'));
const HITLReportDetailPage = lazy(() => import('./pages/admin/HITLReportDetailPage'));
const AdminLogoutPage = lazy(() => import('./pages/admin/LogoutPage'));
const AdminNotificationsPage = lazy(() => import('./pages/admin/NotificationsPage'));
const AdminPatientsPage = lazy(() => import('./pages/admin/PatientsPage'));
const AdminReportDetailPage = lazy(() => import('./pages/admin/AdminReportDetailPage'));
const AdminReportsPage = lazy(() => import('./pages/admin/ReportsPage'));
const AdminSettingsPage = lazy(() => import('./pages/admin/SettingsPage'));
const AdminSystemHealthPage = lazy(() => import('./pages/admin/SystemHealthPage'));
const UsersPage = lazy(() => import('./pages/admin/UsersPage'));
const AnalyticsPage = lazy(() => import('./pages/doctor/AnalyticsPage'));
const AnalyticsOverviewPage = lazy(() => import('./pages/doctor/AnalyticsOverviewPage'));
const DoctorAccountPage = lazy(() => import('./pages/doctor/AccountPage'));
const DoctorDashboard = lazy(() => import('./pages/doctor/DoctorDashboard'));
const HITLQueuePage = lazy(() => import('./pages/doctor/HITLQueuePage'));
const DoctorNotificationsPage = lazy(() => import('./pages/doctor/NotificationsPage'));
const PatientDetailPage = lazy(() => import('./pages/doctor/PatientDetailPage'));
const PatientListPage = lazy(() => import('./pages/doctor/PatientListPage'));
const ReportDetailPage = lazy(() => import('./pages/doctor/ReportDetailPage'));
const DoctorReportsPage = lazy(() => import('./pages/doctor/ReportsPage'));
const UploadPage = lazy(() => import('./pages/doctor/UploadPage'));
const VerificationPendingPage = lazy(() => import('./pages/doctor/VerificationPendingPage'));
const MyReportsPage = lazy(() => import('./pages/patient/MyReportsPage'));
const AccountPage = lazy(() => import('./pages/patient/AccountPage'));
const PatientChatPage = lazy(() => import('./pages/patient/PatientChatPage'));
const PatientDashboard = lazy(() => import('./pages/patient/PatientDashboard'));
const PatientNotificationsPage = lazy(() => import('./pages/patient/NotificationsPage'));
const PatientReportViewPage = lazy(() => import('./pages/patient/ReportViewPage'));
const PatientTrendsPage = lazy(() => import('./pages/patient/TrendsPage'));

function RoleGuard({ role }: { role: User['role'] }) {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== role) {
    return <Navigate to={`/${user?.role ?? 'login'}`} replace />;
  }

  return <Outlet />;
}

function DoctorApprovalGuard() {
  const user = useAuthStore((state) => state.user);

  if (user?.verification_status !== 'approved') {
    return <Navigate to="/doctor/verification-pending" replace />;
  }

  return <Outlet />;
}

function RootRedirect() {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === 'doctor' && user.verification_status !== 'approved') {
    return <Navigate to="/doctor/verification-pending" replace />;
  }

  return <Navigate to={`/${user.role}`} replace />;
}

function LazyRoute({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Skeleton variant="card" rows={3} />}>{children}</Suspense>;
}

function App() {
  return (
    <>
      <NetworkDisconnectedBanner />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        <Route element={<RoleGuard role="doctor" />}>
          <Route path="/doctor/verification-pending" element={<LazyRoute><VerificationPendingPage /></LazyRoute>} />
          <Route element={<DoctorApprovalGuard />}>
            <Route element={<AppShell />}>
              <Route path="/doctor" element={<LazyRoute><DoctorDashboard /></LazyRoute>} />
              <Route path="/doctor/patients" element={<LazyRoute><PatientListPage /></LazyRoute>} />
              <Route path="/doctor/patients/:patientId" element={<LazyRoute><PatientDetailPage /></LazyRoute>} />
              <Route path="/doctor/reports" element={<LazyRoute><DoctorReportsPage /></LazyRoute>} />
              <Route path="/doctor/reports/:reportId" element={<LazyRoute><ReportDetailPage /></LazyRoute>} />
              <Route path="/doctor/upload" element={<LazyRoute><UploadPage /></LazyRoute>} />
              <Route path="/doctor/hitl" element={<LazyRoute><HITLQueuePage /></LazyRoute>} />
              <Route path="/doctor/analytics" element={<LazyRoute><AnalyticsOverviewPage /></LazyRoute>} />
              <Route path="/doctor/analytics/:patientId" element={<LazyRoute><AnalyticsPage /></LazyRoute>} />
              <Route path="/doctor/chat" element={<Navigate to="/doctor" replace />} />
              <Route path="/doctor/notifications" element={<LazyRoute><DoctorNotificationsPage /></LazyRoute>} />
              <Route path="/doctor/account" element={<LazyRoute><DoctorAccountPage /></LazyRoute>} />
              <Route path="/doctor/logout" element={<LazyRoute><AdminLogoutPage /></LazyRoute>} />
            </Route>
          </Route>
        </Route>

        <Route element={<RoleGuard role="patient" />}>
          <Route element={<AppShell />}>
            <Route path="/patient" element={<LazyRoute><PatientDashboard /></LazyRoute>} />
            <Route path="/patient/reports" element={<LazyRoute><MyReportsPage /></LazyRoute>} />
            <Route path="/patient/reports/:reportId" element={<LazyRoute><PatientReportViewPage /></LazyRoute>} />
            <Route path="/patient/trends" element={<LazyRoute><PatientTrendsPage /></LazyRoute>} />
            <Route path="/patient/chat" element={<LazyRoute><PatientChatPage /></LazyRoute>} />
            <Route path="/patient/notifications" element={<LazyRoute><PatientNotificationsPage /></LazyRoute>} />
            <Route path="/patient/account" element={<LazyRoute><AccountPage /></LazyRoute>} />
          </Route>
        </Route>

        <Route element={<RoleGuard role="admin" />}>
          <Route element={<AppShell />}>
            <Route path="/admin" element={<LazyRoute><AdminDashboard /></LazyRoute>} />
            <Route path="/admin/users" element={<LazyRoute><UsersPage /></LazyRoute>} />
            <Route path="/admin/doctors" element={<LazyRoute><AdminDoctorsPage /></LazyRoute>} />
            <Route path="/admin/patients" element={<LazyRoute><AdminPatientsPage /></LazyRoute>} />
            <Route path="/admin/assignments" element={<LazyRoute><AdminAssignmentsPage /></LazyRoute>} />
            <Route path="/admin/reports" element={<LazyRoute><AdminReportsPage /></LazyRoute>} />
            <Route path="/admin/reports/:reportId" element={<LazyRoute><AdminReportDetailPage /></LazyRoute>} />
            <Route path="/admin/failed-jobs" element={<LazyRoute><AdminFailedJobsPage /></LazyRoute>} />
            <Route path="/admin/hitl" element={<LazyRoute><HITLOverviewPage /></LazyRoute>} />
            <Route path="/admin/hitl/:reportId" element={<LazyRoute><HITLReportDetailPage /></LazyRoute>} />
            <Route path="/admin/analytics" element={<LazyRoute><AdminAnalyticsPage /></LazyRoute>} />
            <Route path="/admin/notifications" element={<LazyRoute><AdminNotificationsPage /></LazyRoute>} />
            <Route path="/admin/audit-logs" element={<LazyRoute><AdminAuditLogsPage /></LazyRoute>} />
            <Route path="/admin/system-health" element={<LazyRoute><AdminSystemHealthPage /></LazyRoute>} />
            <Route path="/admin/settings" element={<LazyRoute><AdminSettingsPage /></LazyRoute>} />
            <Route path="/admin/logout" element={<LazyRoute><AdminLogoutPage /></LazyRoute>} />
          </Route>
        </Route>

        <Route path="/" element={<RootRedirect />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </>
  );
}

export default App;
