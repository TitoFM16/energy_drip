import { useState } from 'react';
import {
  useConsentRequestDetail,
  useConsentRequests,
} from '../../features/consents/use-consent-requests';
import { useConsentTemplateVersion } from '../../features/consents/use-consent-templates';
import type { ConsentRequestStatus, EligibilityResult } from '../../features/consents/types';
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

const ELIGIBILITY_STYLES: Record<EligibilityResult, string> = {
  eligible: 'bg-green-50 text-green-700',
  requires_manual_review: 'bg-amber-50 text-amber-700',
  not_eligible: 'bg-red-50 text-red-700',
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
      {requests.isError && <p className="text-red-600">No se pudieron cargar las solicitudes.</p>}
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
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {STATUS_LABELS[request.status]}
                </span>
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
  if (isError || !detail) return <p className="text-red-600">No se pudo cargar el detalle.</p>;

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
          <span
            className={`mb-3 inline-block rounded-full px-2.5 py-1 text-xs font-medium ${ELIGIBILITY_STYLES[detail.submission.eligibility_result]}`}
          >
            {ELIGIBILITY_LABELS[detail.submission.eligibility_result]}
          </span>
          <p className="mb-3 text-xs text-slate-500">
            Enviado {new Date(detail.submission.submitted_at).toLocaleString()} ·{' '}
            {detail.submission.has_signature ? 'Firma capturada' : 'Sin firma'}
          </p>
          <ul className="flex flex-col gap-2">
            {detail.submission.answers.map((answer) => (
              <li key={answer.question_id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                <p className="font-medium text-slate-800">
                  {promptByFieldKey.get(answer.field_key) ?? answer.field_key}
                </p>
                <p className="text-slate-600">{String(answer.value)}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
