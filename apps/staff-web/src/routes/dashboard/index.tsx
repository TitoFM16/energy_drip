import { Badge, Callout } from '@medical-platform/ui';
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useAppointments } from '../../features/appointments/use-appointments';
import { useConsentRequests } from '../../features/consents/use-consent-requests';
import type { ConsentRequest } from '../../features/consents/types';
import { useNotifications } from '../../features/notifications/use-notifications';
import type { NotificationMessage, NotificationStatus } from '../../features/notifications/types';
import { usePatients } from '../../features/patients/use-patients';
import type { Appointment, AppointmentStatus } from '../../features/scheduling/types';
import { PageHeading } from '../../shared/components/app-shell';

const BOGOTA_TIME_ZONE = 'America/Bogota';
const UPCOMING_STATUSES: AppointmentStatus[] = [
  'scheduled',
  'confirmed',
  'consent_pending',
  'consent_completed',
  'checked_in',
];
const EXCEPTION_STATUSES: AppointmentStatus[] = ['cancelled', 'no_show'];

const APPOINTMENT_LABELS: Record<AppointmentStatus, string> = {
  scheduled: 'Programada',
  confirmed: 'Confirmada',
  consent_pending: 'Consentimiento pendiente',
  consent_completed: 'Consentimiento completo',
  checked_in: 'Registrada',
  completed: 'Atendida',
  cancelled: 'Cancelada',
  no_show: 'No asistió',
};

const NOTIFICATION_LABELS: Record<NotificationStatus, string> = {
  pending: 'Pendiente',
  sent: 'Enviada',
  delivered: 'Entregada',
  failed: 'Fallida',
};

const NOTIFICATION_VARIANTS: Record<
  NotificationStatus,
  'neutral' | 'success' | 'warning' | 'danger'
> = {
  pending: 'warning',
  sent: 'neutral',
  delivered: 'success',
  failed: 'danger',
};

function operationalRange() {
  const now = new Date();
  return {
    now: now.getTime(),
    start: new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString(),
    end: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  };
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: BOGOTA_TIME_ZONE,
  }).format(new Date(value));
}

function patientLabel(patientNameById: Map<string, string>, patientId: string): string {
  return patientNameById.get(patientId) ?? `Paciente ${patientId.slice(0, 8)}`;
}

export function DashboardPage() {
  const [range] = useState(operationalRange);
  const appointments = useAppointments(range.start, range.end);
  const pendingConsents = useConsentRequests(undefined, { status: 'pending' });
  const expiredConsents = useConsentRequests(undefined, { status: 'expired' });
  const reviewConsents = useConsentRequests(undefined, { needsReview: true });
  const notifications = useNotifications();
  const patients = usePatients();

  const patientNameById = new Map(
    patients.data?.map((patient) => [patient.id, `${patient.first_name} ${patient.last_name}`]),
  );

  const upcoming =
    appointments.data?.filter(
      (appointment) =>
        new Date(appointment.starts_at).getTime() >= range.now &&
        UPCOMING_STATUSES.includes(appointment.status),
    ) ?? [];
  const scheduleExceptions =
    appointments.data?.filter((appointment) => EXCEPTION_STATUSES.includes(appointment.status)) ??
    [];
  const notificationFailures =
    notifications.data?.filter((message) => message.status === 'failed') ?? [];
  const recentNotifications = notifications.data?.slice(0, 6) ?? [];

  return (
    <div>
      <PageHeading>Dashboard operativo</PageHeading>
      <p className="mb-6 text-sm text-slate-600">
        Estado de la operación clínica. Fechas y horas en Colombia ({BOGOTA_TIME_ZONE}).
      </p>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <DashboardCard title="Próximas citas" count={upcoming.length} to="/agenda">
          <QueryState
            isLoading={appointments.isLoading}
            isError={appointments.isError}
            empty={upcoming.length === 0}
            emptyText="No hay citas próximas en los siguientes 7 días."
            errorText="No se pudieron cargar las próximas citas."
          >
            <AppointmentList appointments={upcoming.slice(0, 6)} patients={patientNameById} />
          </QueryState>
        </DashboardCard>

        <DashboardCard title="Excepciones de agenda" count={scheduleExceptions.length} to="/agenda">
          <QueryState
            isLoading={appointments.isLoading}
            isError={appointments.isError}
            empty={scheduleExceptions.length === 0}
            emptyText="No hay cancelaciones ni inasistencias recientes."
            errorText="No se pudieron cargar las excepciones de agenda."
          >
            <AppointmentList
              appointments={scheduleExceptions.slice(0, 6)}
              patients={patientNameById}
            />
          </QueryState>
        </DashboardCard>

        <DashboardCard
          title="Consentimientos pendientes"
          count={(pendingConsents.data?.length ?? 0) + (expiredConsents.data?.length ?? 0)}
          to="/consents"
        >
          <ConsentGroup
            title="Pendientes"
            requests={pendingConsents.data}
            patients={patientNameById}
            isLoading={pendingConsents.isLoading}
            isError={pendingConsents.isError}
            emptyText="No hay solicitudes pendientes."
          />
          <ConsentGroup
            title="Expirados"
            requests={expiredConsents.data}
            patients={patientNameById}
            isLoading={expiredConsents.isLoading}
            isError={expiredConsents.isError}
            emptyText="No hay solicitudes expiradas."
          />
        </DashboardCard>

        <DashboardCard
          title="Revisión médica"
          count={reviewConsents.data?.length ?? 0}
          to="/consents"
        >
          <QueryState
            isLoading={reviewConsents.isLoading}
            isError={reviewConsents.isError}
            empty={(reviewConsents.data?.length ?? 0) === 0}
            emptyText="No hay envíos que requieran revisión médica."
            errorText="No se pudo cargar la cola de revisión médica."
          >
            <ConsentList
              requests={reviewConsents.data?.slice(0, 6) ?? []}
              patients={patientNameById}
              badgeLabel="Requiere revisión"
              badgeVariant="warning"
            />
          </QueryState>
        </DashboardCard>

        <DashboardCard
          title="Estado de notificaciones"
          count={notificationFailures.length}
          countLabel="fallidas"
          to="/notifications"
          className="xl:col-span-2"
        >
          <QueryState
            isLoading={notifications.isLoading}
            isError={notifications.isError}
            empty={recentNotifications.length === 0}
            emptyText="Todavía no hay notificaciones registradas."
            errorText="No se pudo cargar el estado de las notificaciones."
          >
            <NotificationList messages={recentNotifications} />
          </QueryState>
        </DashboardCard>
      </div>
    </div>
  );
}

function DashboardCard({
  title,
  count,
  countLabel,
  to,
  className = '',
  children,
}: {
  title: string;
  count: number;
  countLabel?: string;
  to: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-4 ${className}`}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold tracking-wide text-slate-700 uppercase">{title}</h2>
          <Badge>
            {count} {countLabel}
          </Badge>
        </div>
        <Link to={to} className="text-sm font-medium text-slate-600 hover:text-slate-900">
          Ver detalle →
        </Link>
      </div>
      {children}
    </section>
  );
}

function QueryState({
  isLoading,
  isError,
  empty,
  emptyText,
  errorText,
  children,
}: {
  isLoading: boolean;
  isError: boolean;
  empty: boolean;
  emptyText: string;
  errorText: string;
  children: ReactNode;
}) {
  if (isLoading) return <p className="text-sm text-slate-500">Cargando...</p>;
  if (isError) return <Callout variant="danger">{errorText}</Callout>;
  if (empty) return <p className="text-sm text-slate-500">{emptyText}</p>;
  return children;
}

function AppointmentList({
  appointments,
  patients,
}: {
  appointments: Appointment[];
  patients: Map<string, string>;
}) {
  return (
    <ul className="divide-y divide-slate-200">
      {appointments.map((appointment) => (
        <li key={appointment.id} className="flex items-start justify-between gap-3 py-3 first:pt-0">
          <div>
            <p className="text-sm font-medium text-slate-900">
              {patientLabel(patients, appointment.patient_id)}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">{formatDateTime(appointment.starts_at)}</p>
          </div>
          <Badge
            variant={
              appointment.status === 'cancelled' || appointment.status === 'no_show'
                ? 'danger'
                : 'neutral'
            }
          >
            {APPOINTMENT_LABELS[appointment.status]}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

function ConsentGroup({
  title,
  requests,
  patients,
  isLoading,
  isError,
  emptyText,
}: {
  title: string;
  requests: ConsentRequest[] | undefined;
  patients: Map<string, string>;
  isLoading: boolean;
  isError: boolean;
  emptyText: string;
}) {
  return (
    <div className="mb-5 last:mb-0">
      <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">{title}</h3>
      <QueryState
        isLoading={isLoading}
        isError={isError}
        empty={(requests?.length ?? 0) === 0}
        emptyText={emptyText}
        errorText={`No se pudieron cargar los consentimientos ${title.toLowerCase()}.`}
      >
        <ConsentList
          requests={requests?.slice(0, 4) ?? []}
          patients={patients}
          badgeLabel={title === 'Pendientes' ? 'Pendiente' : 'Expirado'}
          badgeVariant={title === 'Pendientes' ? 'warning' : 'danger'}
        />
      </QueryState>
    </div>
  );
}

function ConsentList({
  requests,
  patients,
  badgeLabel,
  badgeVariant,
}: {
  requests: ConsentRequest[];
  patients: Map<string, string>;
  badgeLabel: string;
  badgeVariant: 'warning' | 'danger';
}) {
  return (
    <ul className="divide-y divide-slate-200">
      {requests.map((request) => (
        <li key={request.id} className="flex items-start justify-between gap-3 py-3 first:pt-0">
          <div>
            <p className="text-sm font-medium text-slate-900">
              {patientLabel(patients, request.patient_id)}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              {request.status === 'pending' ? 'Expira' : 'Expiró'}{' '}
              {formatDateTime(request.expires_at)}
            </p>
          </div>
          <Badge variant={badgeVariant}>{badgeLabel}</Badge>
        </li>
      ))}
    </ul>
  );
}

function NotificationList({ messages }: { messages: NotificationMessage[] }) {
  return (
    <ul className="grid grid-cols-1 gap-x-6 lg:grid-cols-2">
      {messages.map((message) => (
        <li
          key={message.id}
          className="flex items-start justify-between gap-3 border-t border-slate-200 py-3 first:border-t-0 lg:[&:nth-child(2)]:border-t-0"
        >
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-slate-900">
              {message.template_key} · {message.recipient}
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              WhatsApp · {formatDateTime(message.created_at)}
            </p>
            {message.failure_reason && (
              <p className="mt-1 text-xs text-red-700">{message.failure_reason}</p>
            )}
          </div>
          <Badge variant={NOTIFICATION_VARIANTS[message.status]}>
            {NOTIFICATION_LABELS[message.status]}
          </Badge>
        </li>
      ))}
    </ul>
  );
}
