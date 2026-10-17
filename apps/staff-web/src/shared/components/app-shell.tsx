import type { ReactNode } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth/use-auth';

const NAV_ITEMS = [
  { to: '/agenda', label: 'Agenda' },
  { to: '/patients', label: 'Pacientes' },
  { to: '/treatments', label: 'Servicios' },
  { to: '/consents', label: 'Consentimientos' },
  { to: '/settings', label: 'Equipo y horarios' },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 md:flex-row text-slate-900">
      <aside className="flex shrink-0 flex-col border-b border-slate-200 bg-white p-4 md:w-56 md:border-r md:border-b-0">
        <div className="mb-6 text-lg font-semibold">Energy Drip</div>
        <nav className="flex flex-1 flex-wrap gap-1 md:flex-col">
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
      <main className="min-w-0 flex-1 p-4 sm:p-8">
        <Outlet />
      </main>
    </div>
  );
}

export function PageHeading({ children }: { children: ReactNode }) {
  return <h1 className="mb-6 text-2xl font-semibold text-slate-900">{children}</h1>;
}
