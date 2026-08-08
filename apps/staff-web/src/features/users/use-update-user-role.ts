import type { Schemas } from '@medical-platform/api-client';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { StaffUser } from './types';

export type AssignableRole = Exclude<Schemas['RoleName'], 'platform_admin'>;

interface UpdateUserRoleInput {
  userId: string;
  roles: AssignableRole[];
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, roles }: UpdateUserRoleInput) =>
      apiFetch<StaffUser>(`/api/v1/auth/users/${userId}/roles`, {
        method: 'PATCH',
        body: JSON.stringify({ roles }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
