import { useState } from 'react';
import { usePractitioners } from '../../features/scheduling/use-practitioners';
import { useTreatmentDefinitions } from '../../features/treatments/use-treatment-definitions';
import {
  useCreateTreatmentPlan,
  useTreatmentPlans,
  useUpdateTreatmentPlan,
} from '../../features/treatments/use-treatment-plans';
import {
  useRecordTreatmentSession,
  useTreatmentSessions,
} from '../../features/treatments/use-treatment-sessions';
import type { TreatmentPlanStatus } from '../../features/treatments/types';

const STATUS_LABELS: Record<TreatmentPlanStatus, string> = {
  active: 'Activo',
  completed: 'Completado',
  cancelled: 'Cancelado',
};

interface TreatmentPlansSectionProps {
  patientId: string;
}

export function TreatmentPlansSection({ patientId }: TreatmentPlansSectionProps) {
  const plans = useTreatmentPlans(patientId);
  const definitions = useTreatmentDefinitions();
  const createPlan = useCreateTreatmentPlan();
  const [expandedPlanId, setExpandedPlanId] = useState<string | null>(null);
  const [selectedDefinitionId, setSelectedDefinitionId] = useState('');
  const [sessionCount, setSessionCount] = useState(1);
  const [notes, setNotes] = useState('');

  const definitionById = new Map(definitions.data?.map((d) => [d.id, d]));

  async function handleCreatePlan(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedDefinitionId) return;
    await createPlan.mutateAsync({
      patient_id: patientId,
      treatment_definition_id: selectedDefinitionId,
      planned_session_count: sessionCount,
      notes: notes.trim() || undefined,
    });
    setSelectedDefinitionId('');
    setSessionCount(1);
    setNotes('');
  }

  return (
    <section className="mt-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Tratamientos
      </h2>

      {plans.isLoading && <p className="text-slate-500">Cargando planes...</p>}
      {plans.isError && <p className="text-red-600">No se pudieron cargar los planes.</p>}
      {plans.data && plans.data.length === 0 && (
        <p className="mb-4 text-slate-500">Este paciente no tiene planes de tratamiento.</p>
      )}

      <div className="mb-4 flex flex-col gap-3">
        {plans.data?.map((plan) => (
          <div key={plan.id} className="rounded-lg border border-slate-200 bg-white">
            <button
              type="button"
              onClick={() => setExpandedPlanId((id) => (id === plan.id ? null : plan.id))}
              className="flex w-full items-center justify-between px-4 py-3 text-left"
            >
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {definitionById.get(plan.treatment_definition_id)?.name ?? 'Tratamiento'}
                </p>
                <p className="text-xs text-slate-500">
                  {plan.planned_session_count} sesiones planificadas
                  {plan.notes ? ` · ${plan.notes}` : ''}
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                {STATUS_LABELS[plan.status]}
              </span>
            </button>
            {expandedPlanId === plan.id && <PlanDetail planId={plan.id} status={plan.status} />}
          </div>
        ))}
      </div>

      <form
        onSubmit={handleCreatePlan}
        className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4"
      >
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Tratamiento
          <select
            value={selectedDefinitionId}
            onChange={(e) => {
              setSelectedDefinitionId(e.target.value);
              const definition = definitionById.get(e.target.value);
              if (definition) setSessionCount(definition.default_session_count);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Selecciona un tratamiento...</option>
            {definitions.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Sesiones planificadas
          <input
            type="number"
            min={1}
            value={sessionCount}
            onChange={(e) => setSessionCount(Number(e.target.value))}
            className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Notas
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={!selectedDefinitionId || createPlan.isPending}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {createPlan.isPending ? 'Creando...' : 'Nuevo plan'}
        </button>
      </form>
    </section>
  );
}

function PlanDetail({ planId, status }: { planId: string; status: TreatmentPlanStatus }) {
  const sessions = useTreatmentSessions(planId);
  const practitioners = usePractitioners();
  const recordSession = useRecordTreatmentSession();
  const updatePlan = useUpdateTreatmentPlan();

  const [practitionerId, setPractitionerId] = useState('');
  const [evolution, setEvolution] = useState('');

  async function handleRecordSession(event: React.FormEvent) {
    event.preventDefault();
    if (!practitionerId) return;
    await recordSession.mutateAsync({
      treatment_plan_id: planId,
      practitioner_id: practitionerId,
      session_number: (sessions.data?.length ?? 0) + 1,
      clinical_evolution: evolution.trim() || undefined,
    });
    setEvolution('');
  }

  return (
    <div className="border-t border-slate-100 px-4 py-3">
      {sessions.isLoading && <p className="text-sm text-slate-500">Cargando sesiones...</p>}
      {sessions.data && sessions.data.length === 0 && (
        <p className="text-sm text-slate-500">Sin sesiones registradas todavía.</p>
      )}
      <ul className="mb-3 flex flex-col gap-2">
        {sessions.data?.map((session) => (
          <li key={session.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <p className="font-medium text-slate-800">
              Sesión {session.session_number}
              {session.performed_at && ` — ${new Date(session.performed_at).toLocaleDateString()}`}
            </p>
            {session.clinical_evolution && (
              <p className="text-slate-600">{session.clinical_evolution}</p>
            )}
          </li>
        ))}
      </ul>

      {status === 'active' && (
        <>
          <form onSubmit={handleRecordSession} className="mb-3 flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
              Profesional
              <select
                value={practitionerId}
                onChange={(e) => setPractitionerId(e.target.value)}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Selecciona...</option>
                {practitioners.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-700">
              Evolución clínica
              <input
                type="text"
                value={evolution}
                onChange={(e) => setEvolution(e.target.value)}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              />
            </label>
            <button
              type="submit"
              disabled={!practitionerId || recordSession.isPending}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              {recordSession.isPending ? 'Guardando...' : 'Registrar sesión'}
            </button>
          </form>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={updatePlan.isPending}
              onClick={() => updatePlan.mutate({ planId, status: 'completed' })}
              className="rounded-full border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              Completar plan
            </button>
            <button
              type="button"
              disabled={updatePlan.isPending}
              onClick={() => updatePlan.mutate({ planId, status: 'cancelled' })}
              className="rounded-full border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              Cancelar plan
            </button>
          </div>
        </>
      )}
    </div>
  );
}
