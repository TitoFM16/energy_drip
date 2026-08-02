import { createBrowserRouter } from 'react-router-dom';
import { AcceptInvitePage } from '../routes/accept-invite';
import { AgendaPage } from '../routes/agenda';
import { ConsentsPage } from '../routes/consents';
import { DashboardPage } from '../routes/dashboard';
import { ForgotPasswordPage } from '../routes/forgot-password';
import { LoginPage } from '../routes/login';
import { NotificationsPage } from '../routes/notifications';
import { PatientDetailPage } from '../routes/patients/detail';
import { PatientsPage } from '../routes/patients';
import { ResetPasswordPage } from '../routes/reset-password';
import { SettingsPage } from '../routes/settings';
import { TreatmentsPage } from '../routes/treatments';
import { AppShell } from '../shared/components/app-shell';
import { RequireAuth } from '../shared/components/require-auth';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/reset-password/:token', element: <ResetPasswordPage /> },
  { path: '/accept-invite/:token', element: <AcceptInvitePage /> },
  {
    path: '/',
    element: <RequireAuth />,
    children: [
      {
        path: '/',
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'agenda', element: <AgendaPage /> },
          { path: 'patients', element: <PatientsPage /> },
          { path: 'patients/:patientId', element: <PatientDetailPage /> },
          { path: 'treatments', element: <TreatmentsPage /> },
          { path: 'consents', element: <ConsentsPage /> },
          { path: 'notifications', element: <NotificationsPage /> },
          { path: 'settings', element: <SettingsPage /> },
        ],
      },
    ],
  },
]);
