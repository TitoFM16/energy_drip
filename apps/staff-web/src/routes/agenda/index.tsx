import { Badge, Callout, ErrorText } from '@medical-platform/ui';
import { useEffect, useState } from 'react';
import { useAppointments } from '../../features/appointments/use-appointments';
import { Link } from 'react-router-dom';
import { useTreatmentDefinitions } from '../../features/treatments/use-treatment-definitions';
import { usePractitioners } from '../../features/scheduling/use-practitioners';
import { useAppointmentStatusHistory } from '../../features/scheduling/use-appointment-status-history';
import { useAvailability } from '../../features/scheduling/use-availability';
import { useRescheduleAppointment } from '../../features/scheduling/use-reschedule-appointment';
import { useUpdateAppointmentStatus } from '../../features/scheduling/use-update-appointment-status';
import type {
  Appointment,
  AppointmentStatus,
  AvailableSlot,
} from '../../features/scheduling/types';
import { PageHeading } from '../../shared/components/app-shell';
import { BookingPanel } from './booking-panel';
import { dayRangeClinic, formatTimeClinic, shiftDate, todayClinic } from './date-utils';

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

function appointmentDurationMinutes(appointment: Appointment): number {
  const minutes = Math.round(
    (new Date(appointment.ends_at).getTime() - new Date(appointment.starts_at).getTime()) / 60000,
  );
  return Math.min(480, Math.max(5, minutes));
}

export function AgendaPage() {
  const [date, setDate] = useState(todayClinic());
  const [practitionerId, setPractitionerId] = useState<string | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlot | null>(null);
  const [reschedulingAppointment, setReschedulingAppointment] = useState<Appointment | null>(null);

  const practitioners = usePractitioners(true);
  const services = useTreatmentDefinitions();
  const [serviceId, setServiceId] = useState('');
  const service = services.data?.find((item) => item.id === serviceId);
  const selectedPractitioner = practitioners.data?.find((item) => item.id === practitionerId);
  useEffect(() => {
    if (!serviceId && services.data?.length) setServiceId(services.data[0].id);
  }, [serviceId, services.data]);
  const { start, end } = dayRangeClinic(date);
  const appointments = useAppointments(start, end);
  const availability = useAvailability(
    selectedPractitioner?.is_active && (reschedulingAppointment || service) ? practitionerId : null,
    date,
    reschedulingAppointment
      ? appointmentDurationMinutes(reschedulingAppointment)
      : (service?.duration_minutes ?? 60),
  );
  const updateStatus = useUpdateAppointmentStatus();
  const rescheduleAppointment = useRescheduleAppointment();

  useEffect(() => {
    if (!practitionerId && practitioners.data && practitioners.data.length > 0) {
      setPractitionerId(
        (practitioners.data.find((person) => person.is_active) ?? practitioners.data[0]).id,
      );
    }
  }, [practitionerId, practitioners.data]);

  const dayAppointments =
    appointments.data?.filter((a) => a.practitioner_id === practitionerId) ?? [];

  function appointmentLabel(appointment: Appointment): string {
    return appointment.patient_name ?? 'Paciente';
  }

  async function handleSlotClick(slot: AvailableSlot) {
    if (reschedulingAppointment) {
      try {
        await rescheduleAppointment.mutateAsync({
          appointmentId: reschedulingAppointment.id,
          starts_at: slot.starts_at,
          ends_at: slot.ends_at,
        });
        setReschedulingAppointment(null);
      } catch {
        /* The inline mutation error explains a conflicting slot. */
      }
      return;
    }
    setSelectedSlot(slot);
  }

  return (
    <div>
      <PageHeading>Agenda</PageHeading>
      <p className="mb-5 text-sm text-slate-600">
        Citas y disponibilidad por profesional. Hora de Colombia (UTC−5).
      </p>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <select
          aria-label="Profesional de la agenda"
          value={practitionerId ?? ''}
          onChange={(e) => {
            setPractitionerId(e.target.value || null);
            setSelectedSlot(null);
            setReschedulingAppointment(null);
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          {practitioners.data?.length === 0 && <option value="">Sin profesionales</option>}
          {practitioners.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name}
              {p.specialty ? ` — ${p.specialty}` : ''}
              {!p.is_active ? ' (inactivo)' : ''}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setDate((d) => shiftDate(d, -1));
              setSelectedSlot(null);
            }}
            className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
            aria-label="Día anterior"
          >
            ←
          </button>
          <input
            type="date"
            aria-label="Fecha de la agenda"
            required
            value={date}
            onChange={(e) => {
              if (e.target.value) setDate(e.target.value);
              setSelectedSlot(null);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => {
              setDate((d) => shiftDate(d, 1));
              setSelectedSlot(null);
            }}
            className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
            aria-label="Día siguiente"
          >
            →
          </button>
        </div>
      </div>

      {practitioners.data?.length === 0 && (
        <Callout variant="warning" className="mb-6">
          Agrega a tu primer profesional y sus horarios desde{' '}
          <Link className="underline" to="/settings">
            Equipo y horarios
          </Link>{' '}
          para empezar a recibir citas.
        </Callout>
      )}

      {updateStatus.isError && (
        <ErrorText className="mb-4">
          No se pudo cambiar el estado de la cita. Actualiza la agenda e inténtalo de nuevo.
        </ErrorText>
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
                onReschedule={() => {
                  setSelectedSlot(null);
                  setReschedulingAppointment(appointment);
                }}
                isRescheduling={reschedulingAppointment?.id === appointment.id}
              />
            ))}
          </ul>
        </section>

        <section>
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
            Horarios disponibles
          </h2>
          {selectedPractitioner && !selectedPractitioner.is_active && (
            <p className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
              Este profesional está inactivo. Puedes consultar sus citas; reactívalo en Equipo y
              horarios para agendar o reprogramar.
            </p>
          )}
          {!reschedulingAppointment && (
            <label className="mb-4 flex flex-col gap-1 text-sm font-medium text-slate-700">
              Servicio para la nueva cita
              <select
                value={serviceId}
                onChange={(event) => {
                  setServiceId(event.target.value);
                  setSelectedSlot(null);
                }}
                className="rounded-lg border border-slate-300 px-3 py-2"
              >
                <option value="">Selecciona un servicio</option>
                {services.data?.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} · {item.duration_minutes} min
                  </option>
                ))}
              </select>
            </label>
          )}
          {services.data?.length === 0 && (
            <p className="mb-4 text-sm text-slate-500">
              Agrega un{' '}
              <Link to="/treatments" className="underline">
                servicio
              </Link>{' '}
              para crear citas.
            </p>
          )}
          {selectedSlot && practitionerId && service && !reschedulingAppointment ? (
            <BookingPanel
              practitionerId={practitionerId}
              service={service}
              slot={selectedSlot}
              onClose={() => setSelectedSlot(null)}
              onBooked={() => setSelectedSlot(null)}
            />
          ) : (
            <>
              {reschedulingAppointment && (
                <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  <span>
                    Reprogramando cita de {appointmentLabel(reschedulingAppointment)} — elige un
                    nuevo horario.
                  </span>
                  <button
                    type="button"
                    onClick={() => setReschedulingAppointment(null)}
                    className="shrink-0 underline"
                  >
                    Cancelar
                  </button>
                </div>
              )}
              {rescheduleAppointment.isError && (
                <ErrorText className="mb-3">
                  No se pudo reprogramar la cita. Es posible que el horario ya no esté disponible.
                </ErrorText>
              )}
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
                    disabled={rescheduleAppointment.isPending || !selectedPractitioner?.is_active}
                    onClick={() => handleSlotClick(slot)}
                    className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm text-slate-700 hover:border-slate-900 hover:text-slate-900 disabled:opacity-40"
                  >
                    {formatTimeClinic(slot.starts_at)}
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
  onReschedule,
  isRescheduling,
}: {
  appointment: Appointment;
  label: string;
  updateStatus: ReturnType<typeof useUpdateAppointmentStatus>;
  onReschedule: () => void;
  isRescheduling: boolean;
}) {
  const [showHistory, setShowHistory] = useState(false);
  const history = useAppointmentStatusHistory(appointment.id, showHistory);

  return (
    <li className="flex flex-col gap-2 px-4 py-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-900">
            {formatTimeClinic(appointment.starts_at)}–{formatTimeClinic(appointment.ends_at)}
          </p>
          <p className="text-sm font-medium text-slate-700">{label}</p>
          <p className="text-sm text-slate-500">
            {appointment.treatment_name ?? 'Cita'} · {appointment.practitioner_name}
          </p>
          {appointment.patient_phone && (
            <p className="text-sm text-slate-500">{appointment.patient_phone}</p>
          )}
          {appointment.notes && <p className="mt-1 text-sm text-slate-500">{appointment.notes}</p>}
          <Link to={`/patients/${appointment.patient_id}`} className="text-xs underline">
            Paciente y consentimiento
          </Link>
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
          <button
            type="button"
            onClick={onReschedule}
            className="rounded-full border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40"
          >
            {isRescheduling ? 'Reprogramando…' : 'Reprogramar'}
          </button>
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
              {new Intl.DateTimeFormat('es-CO', {
                dateStyle: 'medium',
                timeStyle: 'short',
                timeZone: 'America/Bogota',
              }).format(new Date(entry.changed_at))}
              {entry.changed_by_full_name ? ` · ${entry.changed_by_full_name}` : ''}
              {entry.reason ? ` · ${entry.reason}` : ''}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
