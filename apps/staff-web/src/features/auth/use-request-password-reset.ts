import { useMutation } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';

interface RequestPasswordResetResponse {
  detail: string;
  // Dev-mode convenience only: the backend returns this outside production
  // so the flow is testable without an email/WhatsApp integration wired up.
  // Never rely on it being present.
  token: string | null;
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: (email: string) =>
      apiFetch<RequestPasswordResetResponse>('/api/v1/auth/password-reset/request', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }),
  });
}
