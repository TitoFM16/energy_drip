// Availability rules and appointment overlap checks treat all timestamps as
// UTC directly, with no per-location timezone conversion yet (a documented
// MVP simplification — see docs/missing_features.md). The Agenda's notion of
// "day" follows that: a plain UTC calendar date, not the browser's local day.

export function todayUTC(): string {
  return new Date().toISOString().slice(0, 10);
}

export function shiftDateUTC(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function dayRangeUTC(date: string): { start: string; end: string } {
  return {
    start: `${date}T00:00:00.000Z`,
    end: `${shiftDateUTC(date, 1)}T00:00:00.000Z`,
  };
}

export function formatTimeUTC(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  });
}
