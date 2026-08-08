import { Badge, Button, Callout, ErrorText } from '@medical-platform/ui';
import { useState } from 'react';
import { useAuth } from '../../features/auth/use-auth';
import type { StaffUser } from '../../features/users/types';
import { type AssignableRole, useUpdateUserRole } from '../../features/users/use-update-user-role';
import { useUsers } from '../../features/users/use-users';

const ROLE_LABELS: Record<AssignableRole, string> = {
  organization_admin: 'Administrador de la organización',
  medical_director: 'Director médico',
  practitioner: 'Profesional',
  assistant: 'Asistente',
  receptionist: 'Recepcionista',
  auditor: 'Auditor',
};

const ASSIGNABLE_ROLES = Object.keys(ROLE_LABELS) as AssignableRole[];

function UserRoleEditor({ staffUser }: { staffUser: StaffUser }) {
  const hasPlatformAdmin = staffUser.roles.includes('platform_admin');
  const initialRoles = staffUser.roles.filter(
    (role): role is AssignableRole => role !== 'platform_admin' && role in ROLE_LABELS,
  );
  const [roles, setRoles] = useState<AssignableRole[]>(initialRoles);
  const updateRole = useUpdateUserRole();

  const normalizedCurrent = [...initialRoles].sort().join('|');
  const normalizedSelected = [...roles].sort().join('|');
  const hasChanges = normalizedCurrent !== normalizedSelected;

  function toggleRole(role: AssignableRole) {
    setRoles((current) =>
      current.includes(role) ? current.filter((item) => item !== role) : [...current, role],
    );
    updateRole.reset();
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    await updateRole.mutateAsync({ userId: staffUser.id, roles });
  }

  const isLastAdminConflict =
    updateRole.error instanceof Error && updateRole.error.message.includes('(409)');

  return (
    <li className="px-4 py-4">
      <form onSubmit={handleSubmit}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-900">{staffUser.full_name}</p>
            <p className="text-xs text-slate-500">{staffUser.email}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {initialRoles.map((role) => (
                <Badge key={role}>{ROLE_LABELS[role]}</Badge>
              ))}
              {hasPlatformAdmin && <Badge variant="warning">Administrador de plataforma</Badge>}
            </div>
          </div>

          <fieldset className="min-w-64 disabled:opacity-60" disabled={hasPlatformAdmin}>
            <legend className="mb-2 text-sm font-medium text-slate-700">
              Roles de {staffUser.full_name}
            </legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {ASSIGNABLE_ROLES.map((role) => (
                <label key={role} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={roles.includes(role)}
                    onChange={() => toggleRole(role)}
                    className="size-4 rounded border-slate-300"
                  />
                  {ROLE_LABELS[role]}
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button
            type="submit"
            size="sm"
            disabled={hasPlatformAdmin || !hasChanges || roles.length === 0 || updateRole.isPending}
          >
            {updateRole.isPending ? 'Guardando...' : `Guardar roles de ${staffUser.full_name}`}
          </Button>
          {roles.length === 0 && (
            <ErrorText>Selecciona al menos un rol antes de guardar.</ErrorText>
          )}
          {updateRole.isSuccess && <span className="text-sm text-green-700">Roles guardados.</span>}
          {hasPlatformAdmin && (
            <span className="text-sm text-slate-500">
              Los roles de plataforma no se administran desde esta clínica.
            </span>
          )}
        </div>

        {updateRole.isError && (
          <ErrorText className="mt-2">
            {isLastAdminConflict
              ? 'No puedes quitar el rol del último administrador. Asigna otro administrador primero.'
              : 'No se pudieron guardar los roles de este usuario.'}
          </ErrorText>
        )}
      </form>
    </li>
  );
}

function UserRolesManager() {
  const users = useUsers();

  return (
    <section className="mt-6">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
        Roles de usuarios
      </h2>
      <p className="mb-4 text-sm text-slate-600">
        Asigna los permisos operativos de cada miembro del equipo. Los cambios quedan registrados en
        la auditoría.
      </p>

      {users.isLoading && <p className="text-slate-500">Cargando usuarios...</p>}
      {users.isError && <ErrorText>No se pudo cargar la lista de usuarios.</ErrorText>}
      {users.data && users.data.length === 0 && (
        <p className="text-slate-500">Todavía no hay usuarios registrados.</p>
      )}

      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {users.data?.map((staffUser) => (
          <UserRoleEditor
            key={`${staffUser.id}:${staffUser.roles.join('|')}`}
            staffUser={staffUser}
          />
        ))}
      </ul>
    </section>
  );
}

export function UserRolesSection() {
  const { user } = useAuth();

  if (!user?.roles.includes('organization_admin')) {
    return (
      <section className="mt-6">
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-500 uppercase">
          Roles de usuarios
        </h2>
        <Callout variant="warning">
          Solo un administrador de la organización puede cambiar roles de usuarios.
        </Callout>
      </section>
    );
  }

  return <UserRolesManager />;
}
