import { useAppointments } from '../../features/appointments/use-appointments';
import { PageHeading } from '../../shared/components/app-shell';

export function AgendaPage() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1).toISOString();
  const { data, isLoading, isError } = useAppointments(start, end);

  return (
    <div>
      <PageHeading>Agenda de hoy</PageHeading>
      {isLoading && <p className="text-slate-500">Cargando citas...</p>}
      {isError && (
        <p className="text-red-600">
          No se pudo cargar la agenda. Verifica que la API esté corriendo.
        </p>
      )}
      {data && data.length === 0 && (
        <p className="text-slate-500">No hay citas programadas para hoy.</p>
      )}
      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {data?.map((appointment) => (
          <li key={appointment.id} className="flex items-center justify-between px-4 py-3">
            <span className="text-sm text-slate-700">
              {new Date(appointment.starts_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
              {appointment.status}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
