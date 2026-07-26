import { useQuery } from '@tanstack/react-query';
import { PageHeading } from '../../shared/components/app-shell';
import { apiFetch } from '../../shared/utilities/api';

interface NotificationMessage {
  id: string;
  channel: string;
  status: string;
  recipient: string;
  template_key: string;
}

export function NotificationsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => apiFetch<NotificationMessage[]>('/api/v1/notifications'),
  });

  return (
    <div>
      <PageHeading>Notificaciones</PageHeading>
      {isLoading && <p className="text-slate-500">Cargando...</p>}
      <div className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {data?.map((message) => (
          <div key={message.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>
              {message.channel} · {message.template_key} · {message.recipient}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium">
              {message.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
