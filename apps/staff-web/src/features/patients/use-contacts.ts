import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '../../shared/utilities/api';
import type { EmergencyContact, PatientContact } from './types';

export function useContacts(patientId: string) {
  return useQuery({
    queryKey: ['contacts', patientId],
    queryFn: () => apiFetch<PatientContact[]>(`/api/v1/patients/${patientId}/contacts`),
    enabled: patientId.length > 0,
  });
}

interface CreateContactInput {
  patient_id: string;
  label: string;
  phone_number?: string;
  email?: string;
}

export function useCreateContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateContactInput) =>
      apiFetch<PatientContact>('/api/v1/patients/contacts', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (contact) => {
      void queryClient.invalidateQueries({ queryKey: ['contacts', contact.patient_id] });
    },
  });
}

export function useDeleteContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId }: { contactId: string; patientId: string }) =>
      apiFetch<void>(`/api/v1/patients/contacts/${contactId}`, { method: 'DELETE' }),
    onSuccess: (_data, { patientId }) => {
      void queryClient.invalidateQueries({ queryKey: ['contacts', patientId] });
    },
  });
}

export function useEmergencyContacts(patientId: string) {
  return useQuery({
    queryKey: ['emergency-contacts', patientId],
    queryFn: () => apiFetch<EmergencyContact[]>(`/api/v1/patients/${patientId}/emergency-contacts`),
    enabled: patientId.length > 0,
  });
}

interface CreateEmergencyContactInput {
  patient_id: string;
  full_name: string;
  relationship?: string;
  phone_number: string;
}

export function useCreateEmergencyContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateEmergencyContactInput) =>
      apiFetch<EmergencyContact>('/api/v1/patients/emergency-contacts', {
        method: 'POST',
        body: JSON.stringify(input),
      }),
    onSuccess: (contact) => {
      void queryClient.invalidateQueries({
        queryKey: ['emergency-contacts', contact.patient_id],
      });
    },
  });
}

export function useDeleteEmergencyContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ contactId }: { contactId: string; patientId: string }) =>
      apiFetch<void>(`/api/v1/patients/emergency-contacts/${contactId}`, { method: 'DELETE' }),
    onSuccess: (_data, { patientId }) => {
      void queryClient.invalidateQueries({ queryKey: ['emergency-contacts', patientId] });
    },
  });
}
