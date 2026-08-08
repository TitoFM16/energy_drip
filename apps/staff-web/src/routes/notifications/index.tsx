import { Badge, Button, ErrorText } from '@medical-platform/ui';
import { useRetryNotification } from '../../features/notifications/use-retry-notification';
import { useNotifications } from '../../features/notifications/use-notifications';
import type { NotificationMessage } from '../../features/notifications/types';
import { PageHeading } from '../../shared/components/app-shell';

const RETRYABLE_TEMPLATE_KEYS = new Set(['appointment_confirmation']);

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
          <NotificationRow key={message.id} message={message} />
        ))}
      </div>
    </div>
  );
}

function NotificationRow({ message }: { message: NotificationMessage }) {
  const retry = useRetryNotification();
  const canRetry = message.status === 'failed' && RETRYABLE_TEMPLATE_KEYS.has(message.template_key);

  return (
    <div className="flex items-start justify-between gap-4 px-4 py-3 text-sm">
      <div>
        <p>
          {message.channel} · {message.template_key} · {message.recipient}
        </p>
        {message.failure_reason && (
          <p className="mt-1 text-xs text-red-700">{message.failure_reason}</p>
        )}
        {retry.isError && (
          <p className="mt-1 text-xs text-red-700">No se pudo reintentar el envío.</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Badge variant={message.status === 'failed' ? 'danger' : 'neutral'}>{message.status}</Badge>
        {canRetry && (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={retry.isPending}
            onClick={() => retry.mutate(message.id)}
          >
            {retry.isPending ? 'Reintentando...' : 'Reintentar'}
          </Button>
        )}
      </div>
    </div>
  );
}
