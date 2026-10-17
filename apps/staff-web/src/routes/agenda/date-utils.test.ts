import { afterEach, describe, expect, it, vi } from 'vitest';
import { dayRangeClinic, formatTimeClinic, shiftDate, todayClinic } from './date-utils';

afterEach(() => vi.useRealTimers());
describe('Colombia appointment dates', () => {
  it('keeps the clinic on the previous calendar date before 05:00 UTC', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-10-17T02:30:00Z'));
    expect(todayClinic()).toBe('2026-10-16');
  });
  it('queries the full clinic day even when it crosses UTC midnight', () => {
    const range = dayRangeClinic('2026-10-16');
    expect(new Date(range.start).toISOString()).toBe('2026-10-16T05:00:00.000Z');
    expect(new Date(range.end).toISOString()).toBe('2026-10-17T05:00:00.000Z');
  });
  it('shows the same local appointment time for offset and UTC API timestamps', () => {
    expect(formatTimeClinic('2026-10-17T14:00:00Z')).toBe(
      formatTimeClinic('2026-10-17T09:00:00-05:00'),
    );
    expect(formatTimeClinic('2026-10-17T14:00:00Z')).toContain('9:00');
  });
  it('moves across year boundaries without changing the selected clinic day', () => {
    expect(shiftDate('2026-12-31', 1)).toBe('2027-01-01');
    expect(shiftDate('2027-01-01', -1)).toBe('2026-12-31');
  });
});
