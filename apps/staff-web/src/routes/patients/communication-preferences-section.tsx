import { Badge, Button, Callout, ErrorText } from '@medical-platform/ui';
import {
  useCommunicationPreferences,
  useUpdateCommunicationPreferences,
} from '../../features/patients/use-communication-preferences';

const BOGOTA_TIME_ZONE = 'America/Bogota';

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: BOGOTA_TIME_ZONE,
  }).format(new Date(value));
}

export function CommunicationPreferencesSection({ patientId }: { patientId: string }) {
  const preferences = useCommunicationPreferences(patientId);
  const updatePreferences = useUpdateCommunicationPreferences(patientId);

  return (
    <section className="mt-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Preferencias de comunicación
      </h2>

      {preferences.isLoading && <p className="text-sm text-slate-500">Cargando preferencias...</p>}
      {preferences.isError && <ErrorText>No se pudieron cargar las preferencias.</ErrorText>}

      {preferences.data && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="mb-1 flex items-center gap-2">
                <p className="text-sm font-medium text-slate-900">WhatsApp</p>
                <Badge variant={preferences.data.whatsapp_opt_out ? 'danger' : 'success'}>
                  {preferences.data.whatsapp_opt_out
                    ? 'Marketing bloqueado'
                    : 'Marketing habilitado'}
                </Badge>
              </div>
              <p className="text-sm text-slate-600">
                {preferences.data.phone_number ?? 'Sin número registrado'}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Primera autorización registrada:{' '}
                {preferences.data.whatsapp_opt_in_at
                  ? formatDateTime(preferences.data.whatsapp_opt_in_at)
                  : 'Sin evidencia registrada'}
              </p>
              {preferences.data.whatsapp_opt_out_at && (
                <p className="mt-1 text-xs text-slate-500">
                  Exclusión registrada: {formatDateTime(preferences.data.whatsapp_opt_out_at)}
                </p>
              )}
            </div>

            <Button
              type="button"
              variant={preferences.data.whatsapp_opt_out ? 'secondary' : 'danger'}
              disabled={!preferences.data.phone_number || updatePreferences.isPending}
              onClick={() => updatePreferences.mutate(!preferences.data!.whatsapp_opt_out)}
            >
              {updatePreferences.isPending
                ? 'Guardando...'
                : preferences.data.whatsapp_opt_out
                  ? 'Reactivar marketing'
                  : 'Bloquear marketing'}
            </Button>
          </div>

          <Callout variant="warning" className="mt-4">
            La exclusión bloquea únicamente mensajes de marketing. Confirmaciones, recordatorios de
            citas y enlaces de consentimiento siguen enviándose por ser comunicaciones clínicas o
            transaccionales.
          </Callout>
          {updatePreferences.isError && (
            <ErrorText className="mt-3">No se pudo actualizar la preferencia.</ErrorText>
          )}
        </div>
      )}
    </section>
  );
}
