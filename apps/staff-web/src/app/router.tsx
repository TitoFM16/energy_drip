import { createBrowserRouter } from 'react-router-dom';
import { AgendaPage } from '../routes/agenda';
import { ConsentsPage } from '../routes/consents';
import { DashboardPage } from '../routes/dashboard';
import { NotificationsPage } from '../routes/notifications';
import { PatientsPage } from '../routes/patients';
import { SettingsPage } from '../routes/settings';
import { TreatmentsPage } from '../routes/treatments';
import { AppShell } from '../shared/components/app-shell';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'agenda', element: <AgendaPage /> },
      { path: 'patients', element: <PatientsPage /> },
      { path: 'treatments', element: <TreatmentsPage /> },
      { path: 'consents', element: <ConsentsPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
]);
