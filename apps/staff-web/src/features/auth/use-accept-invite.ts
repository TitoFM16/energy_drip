import { useMutation } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { TokenResponse } from './types';

interface AcceptInviteInput {
  token: string;
  full_name: string;
  password: string;
}

export function useAcceptInvite() {
  return useMutation({
    mutationFn: ({ token, ...body }: AcceptInviteInput) =>
      apiFetch<TokenResponse>(`/api/v1/auth/invites/${encodeURIComponent(token)}/accept`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  });
}
