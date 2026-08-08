import { Badge, Callout, ErrorText } from '@medical-platform/ui';
import { useEffect, useState } from 'react';
import { useAppointments } from '../../features/appointments/use-appointments';
import { usePatients } from '../../features/patients/use-patients';
import { usePractitioners } from '../../features/scheduling/use-practitioners';
import { useAppointmentStatusHistory } from '../../features/scheduling/use-appointment-status-history';
import { useAvailability } from '../../features/scheduling/use-availability';
import { useUpdateAppointmentStatus } from '../../features/scheduling/use-update-appointment-status';
import type {
  Appointment,
  AppointmentStatus,
  AvailableSlot,
} from '../../features/scheduling/types';
import { PageHeading } from '../../shared/components/app-shell';
import { BookingPanel } from './booking-panel';
import { dayRangeUTC, formatTimeUTC, shiftDateUTC, todayUTC } from './date-utils';

const STATUS_LABELS: Record<AppointmentStatus, string> = {
  scheduled: 'Programada',
  confirmed: 'Confirmada',
  consent_pending: 'Consentimiento pendiente',
  consent_completed: 'Consentimiento completo',
  checked_in: 'Registrada',
  completed: 'Atendida',
  cancelled: 'Cancelada',
  no_show: 'No asistió',
};

const TERMINAL_STATUSES: AppointmentStatus[] = ['completed', 'cancelled', 'no_show'];

const STATUS_ACTIONS: { label: string; status: AppointmentStatus }[] = [
  { label: 'Confirmar', status: 'confirmed' },
  { label: 'Marcar atendida', status: 'completed' },
  { label: 'No asistió', status: 'no_show' },
  { label: 'Cancelar', status: 'cancelled' },
];

export function AgendaPage() {
  const [date, setDate] = useState(todayUTC());
  const [practitionerId, setPractitionerId] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);

  const practitioners = usePractitioners();
  const patients = usePatients();
  const { start, end } = dayRangeUTC(date);
  const appointments = useAppointments(start, end);
  const availability = useAvailability(practitionerId, date, 30);
  const updateStatus = useUpdateAppointmentStatus();

  useEffect(() => {
    if (!practitionerId && practitioners.data && practitioners.data.length > 0) {
      setPractitionerId(practitioners.data[0].id);
    }
  }, [practitionerId, practitioners.data]);

  const patientNameById = new Map(
    patients.data?.map((p) => [p.id, `${p.first_name} ${p.last_name}`]),
  );

  const dayAppointments =
    appointments.data?.filter((a) => a.practitioner_id === practitionerId) ?? [];

  function appointmentLabel(appointment: Appointment): string {
    return patientNameById.get(appointment.patient_id) ?? 'Paciente desconocido';
  }

  return (
    <div>
      <PageHeading>Agenda</PageHeading>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <select
          value={practitionerId ?? ''}
          onChange={(e) => setPractitionerId(e.target.value || null)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          {practitioners.data?.length === 0 && <option value="">Sin profesionales</option>}
          {practitioners.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name}
              {p.specialty ? ` — ${p.specialty}` : ''}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setDate((d) => shiftDateUTC(d, -1))}
            className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
            aria-label="Día anterior"
          >
            ←
          </button>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => setDate((d) => shiftDateUTC(d, 1))}
            className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
            aria-label="Día siguiente"
          >
            →
          </button>
        </div>
      </div>

      {practitioners.data?.length === 0 && (
        <Callout variant="warning" className="mb-6">
          No hay profesionales registrados todavía. Crea uno desde{' '}
          <code className="rounded bg-amber-100 px-1">POST /api/v1/practitioners</code> antes de
          poder agendar citas.
        </Callout>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
            Citas del día
          </h2>
          {appointments.isLoading && <p className="text-slate-500">Cargando citas...</p>}
          {appointments.isError && <ErrorText>No se pudo cargar la agenda del día.</ErrorText>}
          {!appointments.isLoading && dayAppointments.length === 0 && (
            <p className="text-slate-500">No hay citas programadas para este día.</p>
          )}
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {dayAppointments.map((appointment) => (
              <AppointmentRow
                key={appointment.id}
                appointment={appointment}
                label={appointmentLabel(appointment)}
                updateStatus={updateStatus}
              />
            ))}
          </ul>
        </section>

        <section>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
            Horarios disponibles
          </h2>
          {selectedSlot && practitionerId ? (
            <BookingPanel
              practitionerId={practitionerId}
              slot={selectedSlot}
              onClose={() => setSelectedSlot(null)}
              onBooked={() => setSelectedSlot(null)}
            />
          ) : (
            <>
              {availability.isLoading && <p className="text-slate-500">Cargando horarios...</p>}
              {availability.isError && (
                <ErrorText>No se pudieron cargar los horarios disponibles.</ErrorText>
              )}
              {availability.data && availability.data.length === 0 && (
                <p className="text-slate-500">
                  Sin horarios disponibles para este profesional en este día.
                </p>
              )}
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                {availability.data?.map((slot) => (
                  <button
                    key={slot.starts_at}
                    type="button"
                    onClick={() => setSelectedSlot(slot)}
                    className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm text-slate-700 hover:border-slate-900 hover:text-slate-900"
                  >
                    {formatTimeUTC(slot.starts_at)}
                  </button>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function AppointmentRow({
  appointment,
  label,
  updateStatus,
}: {
  appointment: Appointment;
  label: string;
  updateStatus: ReturnType<typeof useUpdateAppointmentStatus>;
}) {
  const [showHistory, setShowHistory] = useState(false);
  const history = useAppointmentStatusHistory(appointment.id, showHistory);

  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-900">
            {formatTimeUTC(appointment.starts_at)}–{formatTimeUTC(appointment.ends_at)}
          </p>
          <p className="text-sm text-slate-500">{label}</p>
        </div>
        <Badge>{STATUS_LABELS[appointment.status]}</Badge>
      </div>
      {!TERMINAL_STATUSES.includes(appointment.status) && (
        <div className="flex flex-wrap gap-2">
          {STATUS_ACTIONS.filter((action) => action.status !== appointment.status).map((action) => (
            <button
              key={action.status}
              type="button"
              disabled={updateStatus.isPending}
              onClick={() =>
                updateStatus.mutate({ appointmentId: appointment.id, status: action.status })
              }
              className="rounded-full border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
      <button
        type="button"
        onClick={() => setShowHistory((v) => !v)}
        className="self-start text-xs text-slate-500 underline"
      >
        {showHistory ? 'Ocultar historial' : 'Ver historial'}
      </button>
      {showHistory && (
        <ul className="flex flex-col gap-1 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {history.isLoading && <li>Cargando historial...</li>}
          {history.isError && <li>No se pudo cargar el historial.</li>}
          {history.data?.map((entry) => (
            <li key={entry.id}>
              {entry.from_status ? STATUS_LABELS[entry.from_status] + ' → ' : ''}
              {STATUS_LABELS[entry.to_status]} ·{' '}
              {new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' }).format(
                new Date(entry.changed_at),
              )}
              {entry.changed_by_full_name ? ` · ${entry.changed_by_full_name}` : ''}
              {entry.reason ? ` · ${entry.reason}` : ''}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
