import { describe, expect, it } from 'vitest';
import { buildBookingRequestPayload, type BookingFormState } from './build-payload';

const BASE_FORM: BookingFormState = {
  first_name: 'Ana',
  last_name: 'Restrepo',
  phone_number: '+573001112233',
  email: '',
  treatment_definition_id: 'treatment-1',
  preferred_date: '',
  message: '',
  website: '',
};

describe('buildBookingRequestPayload', () => {
  it('converts empty optional fields to null', () => {
    const payload = buildBookingRequestPayload(BASE_FORM);
    expect(payload.email).toBeNull();
    expect(payload.preferred_date).toBeNull();
    expect(payload.message).toBeNull();
  });

  it('preserves required fields as-is', () => {
    const payload = buildBookingRequestPayload(BASE_FORM);
    expect(payload.first_name).toBe('Ana');
    expect(payload.last_name).toBe('Restrepo');
    expect(payload.phone_number).toBe('+573001112233');
    expect(payload.treatment_definition_id).toBe('treatment-1');
  });

  it('passes through populated optional fields instead of nulling them', () => {
    const payload = buildBookingRequestPayload({
      ...BASE_FORM,
      email: 'ana@example.com',
      preferred_date: '2026-09-01',
      message: 'Prefiero en la tarde',
    });
    expect(payload.email).toBe('ana@example.com');
    expect(payload.preferred_date).toBe('2026-09-01');
    expect(payload.message).toBe('Prefiero en la tarde');
  });

  it('carries the honeypot field through untouched, including when filled', () => {
    // The component never lets a sighted user fill this in, but the
    // payload builder itself shouldn't special-case or drop it — the
    // filtering happens server-side (see BookingRequestService).
    const payload = buildBookingRequestPayload({ ...BASE_FORM, website: 'https://spam.example' });
    expect(payload.website).toBe('https://spam.example');
  });
});
