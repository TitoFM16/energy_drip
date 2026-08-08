import { Badge, Button, Callout, ErrorText } from '@medical-platform/ui';
import { useState } from 'react';
import { useConsentTemplates } from '../../features/consents/use-consent-templates';
import {
  useConsentRequests,
  useCreateConsentRequest,
  useInvalidateConsentRequest,
  useResendConsentRequest,
} from '../../features/consents/use-consent-requests';

interface ConsentRequestsSectionProps {
  patientId: string;
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  completed: 'Completado',
  expired: 'Expirado',
  invalidated: 'Invalidado',
};

export function ConsentRequestsSection({ patientId }: ConsentRequestsSectionProps) {
  const templates = useConsentTemplates();
  const requests = useConsentRequests(patientId);
  const createRequest = useCreateConsentRequest();
  const invalidateRequest = useInvalidateConsentRequest();
  const resendRequest = useResendConsentRequest();
  const [selectedVersionId, setSelectedVersionId] = useState('');
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [revokeReason, setRevokeReason] = useState('');

  const publishedTemplates = templates.data?.filter((t) => t.latest_version?.published_at) ?? [];

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedVersionId) return;
    await createRequest.mutateAsync({
      patient_id: patientId,
      template_version_id: selectedVersionId,
    });
  }

  async function handleConfirmRevoke(requestId: string) {
    if (!revokeReason.trim()) return;
    await invalidateRequest.mutateAsync({ requestId, reason: revokeReason.trim() });
    setRevokingId(null);
    setRevokeReason('');
  }

  return (
    <section className="mt-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Consentimientos
      </h2>

      {requests.data && requests.data.length === 0 && (
        <p className="mb-3 text-sm text-slate-500">Sin solicitudes de consentimiento todavía.</p>
      )}
      {requests.data && requests.data.length > 0 && (
        <ul className="mb-4 flex flex-col gap-2">
          {requests.data.map((request) => (
            <li key={request.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span>{new Date(request.created_at).toLocaleString()}</span>
                <div className="flex items-center gap-2">
                  <Badge>{STATUS_LABELS[request.status]}</Badge>
                  {request.status === 'pending' && revokingId !== request.id && (
                    <button
                      type="button"
                      onClick={() => setRevokingId(request.id)}
                      className="text-xs text-slate-500 underline"
                    >
                      Revocar
                    </button>
                  )}
                  {(request.status === 'pending' || request.status === 'expired') && (
                    <button
                      type="button"
                      disabled={resendRequest.isPending}
                      onClick={() => resendRequest.mutate(request.id)}
                      className="text-xs text-slate-500 underline disabled:opacity-40"
                    >
                      Reenviar
                    </button>
                  )}
                </div>
              </div>
              {revokingId === request.id && (
                <div className="mt-2 flex flex-wrap items-end gap-2">
                  <input
                    type="text"
                    value={revokeReason}
                    onChange={(e) => setRevokeReason(e.target.value)}
                    placeholder="Motivo de la revocación"
                    className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={!revokeReason.trim() || invalidateRequest.isPending}
                    onClick={() => handleConfirmRevoke(request.id)}
                  >
                    Confirmar revocación
                  </Button>
                  <button
                    type="button"
                    onClick={() => {
                      setRevokingId(null);
                      setRevokeReason('');
                    }}
                    className="text-xs text-slate-500 underline"
                  >
                    Cancelar
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {invalidateRequest.isError && (
        <ErrorText className="mb-3">No se pudo revocar la solicitud.</ErrorText>
      )}
      {resendRequest.isError && (
        <ErrorText className="mb-3">No se pudo reenviar la solicitud.</ErrorText>
      )}
      {resendRequest.data && (
        <Callout variant="warning" className="mb-3 text-xs">
          Solo en desarrollo — nuevo enlace de consentimiento:{' '}
          <code className="break-all rounded bg-amber-100 px-1">
            http://localhost:5174/c/{resendRequest.data.token}
          </code>{' '}
          (en producción se envía por WhatsApp, no se muestra aquí).
        </Callout>
      )}

      <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Plantilla publicada
          <select
            value={selectedVersionId}
            onChange={(e) => setSelectedVersionId(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Selecciona una plantilla...</option>
            {publishedTemplates.map((t) => (
              <option key={t.id} value={t.latest_version!.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <Button type="submit" disabled={!selectedVersionId || createRequest.isPending}>
          {createRequest.isPending ? 'Enviando...' : 'Solicitar consentimiento'}
        </Button>
      </form>
      {publishedTemplates.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">
          No hay plantillas publicadas todavía — créalas desde Consentimientos.
        </p>
      )}
      {createRequest.isError && (
        <ErrorText className="mt-2">No se pudo crear la solicitud.</ErrorText>
      )}
      {createRequest.data && (
        <Callout variant="warning" className="mt-3 text-xs">
          Solo en desarrollo — enlace de consentimiento:{' '}
          <code className="break-all rounded bg-amber-100 px-1">
            http://localhost:5174/c/{createRequest.data.token}
          </code>{' '}
          (en producción se envía por WhatsApp, no se muestra aquí).
        </Callout>
      )}
    </section>
  );
}
