import { Button, ErrorText } from '@medical-platform/ui';
import { useState } from 'react';
import {
  useAvailabilityRules,
  useCreateAvailabilityRule,
  useDeleteAvailabilityRule,
} from '../../features/scheduling/use-availability-rules';
import { usePractitioners } from '../../features/scheduling/use-practitioners';

const WEEKDAY_LABELS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export function AvailabilityRulesSection() {
  const practitioners = usePractitioners();
  const [practitionerId, setPractitionerId] = useState('');

  const rules = useAvailabilityRules(practitionerId);
  const createRule = useCreateAvailabilityRule();
  const deleteRule = useDeleteAvailabilityRule();

  const [weekday, setWeekday] = useState('0');
  const [startTime, setStartTime] = useState('09:00');
  const [endTime, setEndTime] = useState('17:00');

  const sortedRules = [...(rules.data ?? [])].sort(
    (a, b) => a.weekday - b.weekday || a.start_time.localeCompare(b.start_time),
  );

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!practitionerId) return;
    await createRule.mutateAsync({
      practitioner_id: practitionerId,
      weekday: Number(weekday),
      start_time: startTime,
      end_time: endTime,
    });
  }

  return (
    <section className="mt-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Horarios de disponibilidad
      </h2>

      <label className="mb-4 flex flex-col gap-1 text-sm font-medium text-slate-700">
        Profesional
        <select
          value={practitionerId}
          onChange={(e) => setPractitionerId(e.target.value)}
          className="w-full max-w-sm rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">Selecciona un profesional...</option>
          {practitioners.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name}
            </option>
          ))}
        </select>
      </label>

      {practitionerId && (
        <>
          {rules.isLoading && <p className="text-slate-500">Cargando horarios...</p>}
          {rules.isError && <ErrorText>No se pudieron cargar los horarios.</ErrorText>}
          {sortedRules.length === 0 && !rules.isLoading && (
            <p className="mb-4 text-slate-500">
              Este profesional todavía no tiene horarios de disponibilidad.
            </p>
          )}

          <ul className="mb-4 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {sortedRules.map((rule) => (
              <li key={rule.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="text-sm text-slate-900">
                  {WEEKDAY_LABELS[rule.weekday]} · {rule.start_time.slice(0, 5)}–
                  {rule.end_time.slice(0, 5)}
                </span>
                <button
                  type="button"
                  disabled={deleteRule.isPending}
                  onClick={() => deleteRule.mutate({ ruleId: rule.id, practitionerId })}
                  className="text-xs text-slate-500 underline disabled:opacity-40"
                >
                  Eliminar
                </button>
              </li>
            ))}
          </ul>

          <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Día
              <select
                value={weekday}
                onChange={(e) => setWeekday(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {WEEKDAY_LABELS.map((label, index) => (
                  <option key={label} value={index}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Desde
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
              Hasta
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <Button type="submit" disabled={createRule.isPending}>
              {createRule.isPending ? 'Agregando...' : 'Agregar horario'}
            </Button>
          </form>
          {createRule.isError && (
            <ErrorText className="mt-2">
              No se pudo agregar el horario (revisa que la hora de fin sea posterior a la de
              inicio).
            </ErrorText>
          )}
        </>
      )}
    </section>
  );
}
