import { useEffect, useState } from 'react';
import { apiFetch } from '../../shared/api';

export interface PublicService {
  id: string;
  name: string;
  description: string | null;
  price: string;
  currency: string;
  duration_minutes: number;
  image_url: string | null;
}
export interface PublicPractitioner {
  id: string;
  full_name: string;
  specialty: string | null;
}
export interface AvailableSlot {
  starts_at: string;
  ends_at: string;
}
export function formatPrice(price: string, currency: string) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(Number(price));
}
export function formatAppointment(iso: string) {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'long',
    timeStyle: 'short',
    timeZone: 'America/Bogota',
  }).format(new Date(iso));
}
export function localDate() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
}
export function useCatalogue() {
  const [services, setServices] = useState<PublicService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);
    apiFetch<PublicService[]>('/api/v1/public/treatments')
      .then((data) => {
        if (active) setServices(data);
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [attempt]);
  return { services, loading, error, retry: () => setAttempt((value) => value + 1) };
}
