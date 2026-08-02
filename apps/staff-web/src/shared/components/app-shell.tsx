import type { ReactNode } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth/use-auth';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/agenda', label: 'Agenda' },
  { to: '/patients', label: 'Pacientes' },
  { to: '/treatments', label: 'Tratamientos' },
  { to: '/consents', label: 'Consentimientos' },
  { to: '/notifications', label: 'Notificaciones' },
  { to: '/settings', label: 'Configuración' },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white p-4">
        <div className="mb-6 text-lg font-semibold">Medical Platform</div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium ${
                  isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-200 pt-3">
          {user && <p className="mb-2 truncate text-xs text-slate-500">{user.email}</p>}
          <button
            type="button"
            onClick={handleLogout}
            className="w-full rounded-md px-3 py-2 text-left text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}

export function PageHeading({ children }: { children: ReactNode }) {
  return <h1 className="mb-6 text-2xl font-semibold text-slate-900">{children}</h1>;
}
