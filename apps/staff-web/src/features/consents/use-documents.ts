import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { DocumentDownload, DocumentVerifyResult } from './types';

export function useDownloadDocument() {
  return useMutation({
    mutationFn: (documentId: string) =>
      apiFetch<DocumentDownload>(`/api/v1/documents/${documentId}/download`),
  });
}

export function useVerifyDocument() {
  return useMutation({
    mutationFn: (documentId: string) =>
      apiFetch<DocumentVerifyResult>(`/api/v1/documents/${documentId}/verify`, {
        method: 'POST',
      }),
  });
}

export function useInvalidateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, reason }: { documentId: string; reason: string }) =>
      apiFetch(`/api/v1/documents/${documentId}/invalidate`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['consent-requests'] });
    },
  });
}

export function useRegenerateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, reason }: { documentId: string; reason: string }) =>
      apiFetch(`/api/v1/documents/${documentId}/regenerate`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['consent-requests'] });
    },
  });
}
