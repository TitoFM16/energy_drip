import { Badge, Button, ErrorText } from '@medical-platform/ui';
import { useState } from 'react';
import {
  useConsentRequestDetail,
  useConsentRequests,
} from '../../features/consents/use-consent-requests';
import { useConsentTemplateVersion } from '../../features/consents/use-consent-templates';
import type {
  ConsentRequestStatus,
  Document as ConsentDocument,
  EligibilityResult,
} from '../../features/consents/types';
import {
  useDownloadDocument,
  useInvalidateDocument,
  useRegenerateDocument,
  useVerifyDocument,
} from '../../features/consents/use-documents';
import { usePatients } from '../../features/patients/use-patients';

const STATUS_LABELS: Record<ConsentRequestStatus, string> = {
  pending: 'Pendiente',
  completed: 'Completado',
  expired: 'Expirado',
  invalidated: 'Invalidado',
};

const ELIGIBILITY_LABELS: Record<EligibilityResult, string> = {
  eligible: 'Elegible',
  requires_manual_review: 'Requiere revisión médica',
  not_eligible: 'No elegible',
};

const ELIGIBILITY_BADGE_VARIANT: Record<EligibilityResult, 'success' | 'warning' | 'danger'> = {
  eligible: 'success',
  requires_manual_review: 'warning',
  not_eligible: 'danger',
};

export function ReviewSection() {
  const requests = useConsentRequests();
  const patients = usePatients();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const patientNameById = new Map(
    patients.data?.map((p) => [p.id, `${p.first_name} ${p.last_name}`]),
  );

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Revisión de consentimientos
      </h2>

      {requests.isLoading && <p className="text-slate-500">Cargando solicitudes...</p>}
      {requests.isError && <ErrorText>No se pudieron cargar las solicitudes.</ErrorText>}
      {requests.data && requests.data.length === 0 && (
        <p className="text-slate-500">Todavía no hay solicitudes de consentimiento.</p>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {requests.data?.map((request) => (
            <li key={request.id}>
              <button
                type="button"
                onClick={() => setSelectedId(request.id)}
                className={`flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50 ${
                  selectedId === request.id ? 'bg-slate-50' : ''
                }`}
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {patientNameById.get(request.patient_id) ?? 'Paciente'}
                  </p>
                  <p className="text-xs text-slate-500">
                    {new Date(request.created_at).toLocaleString()}
                  </p>
                </div>
                <Badge>{STATUS_LABELS[request.status]}</Badge>
              </button>
            </li>
          ))}
        </ul>

        {selectedId && <RequestDetail requestId={selectedId} />}
      </div>
    </section>
  );
}

function RequestDetail({ requestId }: { requestId: string }) {
  const { data: detail, isLoading, isError } = useConsentRequestDetail(requestId);
  const version = useConsentTemplateVersion(detail?.template_version_id ?? null);

  if (isLoading) return <p className="text-slate-500">Cargando detalle...</p>;
  if (isError || !detail) return <ErrorText>No se pudo cargar el detalle.</ErrorText>;

  const promptByFieldKey = new Map(version.data?.questions.map((q) => [q.field_key, q.prompt]));

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="mb-1 text-sm font-medium text-slate-900">
        Estado: {STATUS_LABELS[detail.status]}
      </p>
      <p className="mb-4 text-xs text-slate-500">
        Expira: {new Date(detail.expires_at).toLocaleString()}
      </p>

      {!detail.submission && <p className="text-sm text-slate-500">Sin envío todavía.</p>}

      {detail.submission && (
        <>
          <Badge
            variant={ELIGIBILITY_BADGE_VARIANT[detail.submission.eligibility_result]}
            className="mb-3"
          >
            {ELIGIBILITY_LABELS[detail.submission.eligibility_result]}
          </Badge>
          <p className="mb-3 text-xs text-slate-500">
            Enviado {new Date(detail.submission.submitted_at).toLocaleString()} ·{' '}
            {detail.submission.has_signature ? 'Firma capturada' : 'Sin firma'}
          </p>
          <ul className="mb-4 flex flex-col gap-2">
            {detail.submission.answers.map((answer) => (
              <li key={answer.question_id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <p className="font-medium text-slate-800">
                  {promptByFieldKey.get(answer.field_key) ?? answer.field_key}
                </p>
                <p className="text-slate-600">{String(answer.value)}</p>
              </li>
            ))}
          </ul>

          {detail.submission.documents.length === 0 && (
            <p className="text-sm text-slate-500">
              Generando documento firmado... Actualiza en unos segundos.
            </p>
          )}
          {detail.submission.documents.length > 0 && (
            <div>
              <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                Documento firmado
              </h3>
              <ul className="flex flex-col gap-2">
                {[...detail.submission.documents]
                  .sort((a, b) => b.document_version - a.document_version)
                  .map((document) => (
                    <DocumentRow key={document.id} document={document} />
                  ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function DocumentRow({ document }: { document: ConsentDocument }) {
  const download = useDownloadDocument();
  const verify = useVerifyDocument();
  const invalidate = useInvalidateDocument();
  const regenerate = useRegenerateDocument();
  const [showInvalidateForm, setShowInvalidateForm] = useState(false);
  const [showRegenerateForm, setShowRegenerateForm] = useState(false);
  const [reason, setReason] = useState('');

  async function handleDownload() {
    const result = await download.mutateAsync(document.id);
    window.open(result.url, '_blank', 'noopener,noreferrer');
  }

  async function handleConfirmInvalidate() {
    if (!reason.trim()) return;
    await invalidate.mutateAsync({ documentId: document.id, reason: reason.trim() });
    setShowInvalidateForm(false);
    setReason('');
  }

  async function handleConfirmRegenerate() {
    if (!reason.trim()) return;
    await regenerate.mutateAsync({ documentId: document.id, reason: reason.trim() });
    setShowRegenerateForm(false);
    setReason('');
  }

  return (
    <li className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="text-slate-800">
          Versión {document.document_version}
          {document.regenerated_reason ? ` · ${document.regenerated_reason}` : ''}
        </span>
        <div className="flex items-center gap-2">
          {document.invalidated_at ? (
            <Badge variant="danger">Invalidado</Badge>
          ) : document.is_current ? (
            <Badge variant="success">Vigente</Badge>
          ) : (
            <Badge>Reemplazado</Badge>
          )}
        </div>
      </div>

      <div className="mt-1 flex flex-wrap items-center gap-3 text-xs">
        <button
          type="button"
          disabled={download.isPending}
          onClick={handleDownload}
          className="text-slate-500 underline disabled:opacity-40"
        >
          Descargar
        </button>
        <button
          type="button"
          disabled={verify.isPending}
          onClick={() => verify.mutate(document.id)}
          className="text-slate-500 underline disabled:opacity-40"
        >
          Verificar
        </button>
        {document.is_current && !document.invalidated_at && (
          <>
            <button
              type="button"
              onClick={() => setShowInvalidateForm((v) => !v)}
              className="text-slate-500 underline"
            >
              Invalidar
            </button>
            <button
              type="button"
              onClick={() => setShowRegenerateForm((v) => !v)}
              className="text-slate-500 underline"
            >
              Regenerar
            </button>
          </>
        )}
      </div>

      {verify.data && (
        <p className={`mt-1 text-xs ${verify.data.matches ? 'text-emerald-700' : 'text-red-600'}`}>
          {verify.data.matches
            ? 'Integridad verificada: el hash coincide.'
            : 'Alerta: el hash almacenado no coincide con el archivo.'}
        </p>
      )}

      {(showInvalidateForm || showRegenerateForm) && (
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Motivo"
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
          />
          {showInvalidateForm && (
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={!reason.trim() || invalidate.isPending}
              onClick={handleConfirmInvalidate}
            >
              Confirmar invalidación
            </Button>
          )}
          {showRegenerateForm && (
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={!reason.trim() || regenerate.isPending}
              onClick={handleConfirmRegenerate}
            >
              Confirmar regeneración
            </Button>
          )}
        </div>
      )}
      {regenerate.isSuccess && (
        <p className="mt-1 text-xs text-slate-500">
          Regeneración solicitada — actualiza en unos segundos para ver la nueva versión.
        </p>
      )}
    </li>
  );
}
