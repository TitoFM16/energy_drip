import { Button, ErrorText, TextField } from '@medical-platform/ui';
import { useState } from 'react';
import { usePractitioners } from '../../features/scheduling/use-practitioners';
import { useCreatePractitioner } from '../../features/scheduling/use-create-practitioner';
import { useUpdatePractitioner } from '../../features/scheduling/use-update-practitioner';
import type { Practitioner } from '../../features/scheduling/types';

function WorkerRow({ worker }: { worker: Practitioner }) {
  const update = useUpdatePractitioner();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(worker.full_name);
  const [specialty, setSpecialty] = useState(worker.specialty ?? '');
  async function save(event: React.FormEvent) {
    event.preventDefault();
    try {
      await update.mutateAsync({
        practitionerId: worker.id,
        full_name: name.trim(),
        specialty: specialty.trim(),
      });
      setEditing(false);
    } catch {
      /* Error is shown below. */
    }
  }
  return (
    <li className="px-4 py-4">
      {editing ? (
        <form className="flex flex-wrap items-end gap-3" onSubmit={save}>
          <TextField
            label="Nombre del profesional"
            required
            maxLength={150}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <TextField
            label="Especialidad (opcional)"
            value={specialty}
            onChange={(event) => setSpecialty(event.target.value)}
          />
          <Button type="submit" size="sm" disabled={update.isPending}>
            Guardar profesional
          </Button>
          <button type="button" onClick={() => setEditing(false)} className="text-sm underline">
            Cancelar
          </button>
        </form>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-medium">{worker.full_name}</p>
            <p className="text-sm text-slate-500">
              {worker.specialty || 'Profesional de atención'} ·{' '}
              {worker.is_active ? 'Disponible para reservar' : 'Inactivo'}
            </p>
          </div>
          <div className="flex gap-4">
            <button type="button" className="text-sm underline" onClick={() => setEditing(true)}>
              Editar
            </button>
            <button
              type="button"
              disabled={update.isPending}
              className="text-sm underline disabled:opacity-40"
              onClick={() =>
                update.mutate({ practitionerId: worker.id, is_active: !worker.is_active })
              }
            >
              {worker.is_active ? 'Desactivar' : 'Reactivar'}
            </button>
          </div>
        </div>
      )}
      {update.isError && (
        <ErrorText className="mt-2">No se pudo actualizar el profesional.</ErrorText>
      )}
    </li>
  );
}
export function PractitionersSection() {
  const practitioners = usePractitioners(true);
  const create = useCreatePractitioner();
  const [name, setName] = useState('');
  const [specialty, setSpecialty] = useState('');
  async function add(event: React.FormEvent) {
    event.preventDefault();
    try {
      await create.mutateAsync({
        full_name: name.trim(),
        specialty: specialty.trim() || undefined,
      });
      setName('');
      setSpecialty('');
    } catch {
      /* Error is shown below. */
    }
  }
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold">Profesionales y trabajadores</h2>
      <p className="mb-4 text-sm text-slate-600">
        Crea un perfil para cada persona de tu equipo. Luego agrega sus horarios de atención.
      </p>
      {practitioners.isLoading && <p>Cargando equipo…</p>}
      {practitioners.isError && <ErrorText>No se pudo cargar el equipo.</ErrorText>}
      {!practitioners.isLoading && practitioners.data?.length === 0 && (
        <p className="mb-4 text-slate-500">
          Agrega al primer profesional para habilitar las reservas.
        </p>
      )}
      <ul className="mb-5 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {practitioners.data?.map((worker) => (
          <WorkerRow key={`${worker.id}:${worker.full_name}:${worker.specialty}`} worker={worker} />
        ))}
      </ul>
      <form onSubmit={add} className="flex flex-wrap items-end gap-3">
        <TextField
          label="Nombre completo"
          required
          maxLength={150}
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <TextField
          label="Especialidad (opcional)"
          maxLength={150}
          value={specialty}
          onChange={(event) => setSpecialty(event.target.value)}
        />
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Agregando…' : 'Agregar profesional'}
        </Button>
      </form>
      {create.isError && <ErrorText className="mt-3">No se pudo agregar el profesional.</ErrorText>}
      <p className="mt-3 text-xs text-slate-500">
        Desactivar un profesional oculta sus horarios al público y conserva sus citas.
      </p>
    </section>
  );
}
