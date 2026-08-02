import { useMutation } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';

interface ResetPasswordInput {
  token: string;
  new_password: string;
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (input: ResetPasswordInput) =>
      apiFetch<void>('/api/v1/auth/password-reset/confirm', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
  });
}
