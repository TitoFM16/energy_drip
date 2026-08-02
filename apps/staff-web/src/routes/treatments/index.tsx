import { Button, ErrorText, TextField } from '@medical-platform/ui';
import { useState } from 'react';
import {
  useCreateTreatmentDefinition,
  useTreatmentDefinitions,
  useUpdateTreatmentDefinition,
} from '../../features/treatments/use-treatment-definitions';
import { PageHeading } from '../../shared/components/app-shell';

export function TreatmentsPage() {
  const definitions = useTreatmentDefinitions(true);
  const createDefinition = useCreateTreatmentDefinition();
  const updateDefinition = useUpdateTreatmentDefinition();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sessionCount, setSessionCount] = useState(1);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    await createDefinition.mutateAsync({
      name,
      description: description.trim() || undefined,
      default_session_count: sessionCount,
    });
    setName('');
    setDescription('');
    setSessionCount(1);
  }

  return (
    <div>
      <PageHeading>Tratamientos</PageHeading>
      <p className="mb-6 text-slate-600">
        Catálogo de tratamientos. Los planes por paciente y sus sesiones se gestionan desde la ficha
        de cada paciente.
      </p>

      {definitions.isLoading && <p className="text-slate-500">Cargando catálogo...</p>}
      {definitions.isError && <ErrorText>No se pudo cargar el catálogo.</ErrorText>}
      {definitions.data && definitions.data.length === 0 && (
        <p className="mb-4 text-slate-500">Todavía no hay tratamientos en el catálogo.</p>
      )}

      <ul className="mb-6 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {definitions.data?.map((definition) => (
          <li key={definition.id} className="flex items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-900">{definition.name}</p>
              <p className="text-xs text-slate-500">
                {definition.description ?? 'Sin descripción'} · {definition.default_session_count}{' '}
                sesiones por defecto
              </p>
            </div>
            <button
              type="button"
              disabled={updateDefinition.isPending}
              onClick={() =>
                updateDefinition.mutate({
                  definitionId: definition.id,
                  is_active: !definition.is_active,
                })
              }
              className={`shrink-0 rounded-full border px-2.5 py-1 text-xs disabled:opacity-40 ${
                definition.is_active
                  ? 'border-slate-300 text-slate-600 hover:bg-slate-50'
                  : 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'
              }`}
            >
              {definition.is_active ? 'Activo' : 'Inactivo — reactivar'}
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
        <TextField
          label="Nombre"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField
          label="Descripción"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <TextField
          label="Sesiones por defecto"
          type="number"
          min={1}
          required
          value={sessionCount}
          onChange={(e) => setSessionCount(Number(e.target.value))}
          className="w-32"
        />
        <Button type="submit" disabled={createDefinition.isPending}>
          {createDefinition.isPending ? 'Agregando...' : 'Agregar tratamiento'}
        </Button>
      </form>
      {createDefinition.isError && (
        <ErrorText className="mt-2">No se pudo agregar el tratamiento.</ErrorText>
      )}
    </div>
  );
}
