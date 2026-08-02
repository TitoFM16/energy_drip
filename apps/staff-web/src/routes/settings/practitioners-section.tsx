import { useState } from 'react';
import { usePractitioners } from '../../features/scheduling/use-practitioners';
import { useCreatePractitioner } from '../../features/scheduling/use-create-practitioner';
import { useUpdatePractitioner } from '../../features/scheduling/use-update-practitioner';
import { useUsers } from '../../features/users/use-users';

export function PractitionersSection() {
  const practitioners = usePractitioners(true);
  const users = useUsers();
  const createPractitioner = useCreatePractitioner();
  const updatePractitioner = useUpdatePractitioner();

  const [userId, setUserId] = useState('');
  const [specialty, setSpecialty] = useState('');

  const practitionerUserIds = new Set(practitioners.data?.map((p) => p.user_id));
  const eligibleUsers = users.data?.filter((u) => !practitionerUserIds.has(u.id)) ?? [];

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!userId) return;
    await createPractitioner.mutateAsync({
      user_id: userId,
      specialty: specialty.trim() || undefined,
    });
    setUserId('');
    setSpecialty('');
  }

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Profesionales
      </h2>

      {practitioners.isLoading && <p className="text-slate-500">Cargando profesionales...</p>}
      {practitioners.isError && (
        <p className="text-red-600">No se pudo cargar la lista de profesionales.</p>
      )}
      {practitioners.data && practitioners.data.length === 0 && (
        <p className="mb-4 text-slate-500">Todavía no hay profesionales registrados.</p>
      )}

      <ul className="mb-6 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {practitioners.data?.map((practitioner) => (
          <li key={practitioner.id} className="flex items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-slate-900">{practitioner.full_name}</p>
              <p className="text-xs text-slate-500">{practitioner.email}</p>
            </div>
            <input
              type="text"
              defaultValue={practitioner.specialty ?? ''}
              placeholder="Especialidad"
              onBlur={(e) => {
                const value = e.target.value.trim();
                if (value !== (practitioner.specialty ?? '')) {
                  updatePractitioner.mutate({ practitionerId: practitioner.id, specialty: value });
                }
              }}
              className="w-40 rounded-lg border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              type="button"
              disabled={updatePractitioner.isPending}
              onClick={() =>
                updatePractitioner.mutate({
                  practitionerId: practitioner.id,
                  is_active: !practitioner.is_active,
                })
              }
              className={`rounded-full border px-2.5 py-1 text-xs disabled:opacity-40 ${
                practitioner.is_active
                  ? 'border-slate-300 text-slate-600 hover:bg-slate-50'
                  : 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'
              }`}
            >
              {practitioner.is_active ? 'Activo' : 'Inactivo — reactivar'}
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Usuario
          <select
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Selecciona un usuario...</option>
            {eligibleUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name} ({u.email})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Especialidad (opcional)
          <input
            type="text"
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={!userId || createPractitioner.isPending}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {createPractitioner.isPending ? 'Agregando...' : 'Agregar profesional'}
        </button>
      </form>
      {eligibleUsers.length === 0 && users.data && users.data.length > 0 && (
        <p className="mt-2 text-sm text-slate-500">
          Todos los usuarios ya tienen un perfil de profesional.
        </p>
      )}
      {createPractitioner.isError && (
        <p className="mt-2 text-sm text-red-600">No se pudo agregar el profesional.</p>
      )}
    </section>
  );
}
