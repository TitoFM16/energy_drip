// Clinic scheduling uses Colombia time, which is UTC-5 year-round.
export const CLINIC_TIMEZONE = 'America/Bogota';
export function todayClinic(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: CLINIC_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
}
export function shiftDate(date: string, days: number): string {
  const value = new Date(`${date}T12:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}
export function dayRangeClinic(date: string): { start: string; end: string } {
  return { start: `${date}T00:00:00-05:00`, end: `${shiftDate(date, 1)}T00:00:00-05:00` };
}
export function formatTimeClinic(iso: string): string {
  return new Intl.DateTimeFormat('es-CO', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: CLINIC_TIMEZONE,
  }).format(new Date(iso));
}
