import { Badge, ErrorText } from '@medical-platform/ui';
import { useNotifications } from '../../features/notifications/use-notifications';
import { PageHeading } from '../../shared/components/app-shell';

export function NotificationsPage() {
  const { data, isLoading, isError } = useNotifications();

  return (
    <div>
      <PageHeading>Notificaciones</PageHeading>
      {isLoading && <p className="text-slate-500">Cargando...</p>}
      {isError && <ErrorText>No se pudieron cargar las notificaciones.</ErrorText>}
      {data?.length === 0 && <p className="text-slate-500">Todavía no hay notificaciones.</p>}
      <div className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {data?.map((message) => (
          <div
            key={message.id}
            className="flex items-start justify-between gap-4 px-4 py-3 text-sm"
          >
            <div>
              <p>
                {message.channel} · {message.template_key} · {message.recipient}
              </p>
              {message.failure_reason && (
                <p className="mt-1 text-xs text-red-700">{message.failure_reason}</p>
              )}
            </div>
            <Badge variant={message.status === 'failed' ? 'danger' : 'neutral'}>
              {message.status}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
