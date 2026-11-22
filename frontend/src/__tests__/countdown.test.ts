import { describe, it, expect } from 'vitest';
import {
  getDeadlineState,
  formatCountdown,
  calculateServerOffset,
} from '../lib/time';

describe('Deadline calculation and states (SPEC 8.3)', () => {
  it('identifies ACTIVE when > 24 hours remaining', () => {
    expect(getDeadlineState(25 * 3600)).toBe('ACTIVE');
    expect(getDeadlineState(48 * 3600)).toBe('ACTIVE');
  });

  it('identifies URGENT at boundary and between 6h and 24h', () => {
    // Boundary: exactly 24h is URGENT
    expect(getDeadlineState(24 * 3600)).toBe('URGENT');
    expect(getDeadlineState(12 * 3600)).toBe('URGENT');
    expect(getDeadlineState(6 * 3600 + 1)).toBe('URGENT');
  });

  it('identifies CRITICAL at boundary and between 0 and 6h', () => {
    // Boundary: exactly 6h is CRITICAL
    expect(getDeadlineState(6 * 3600)).toBe('CRITICAL');
    expect(getDeadlineState(3 * 3600)).toBe('CRITICAL');
    expect(getDeadlineState(1)).toBe('CRITICAL');
  });

  it('identifies EXPIRED when <= 0 remaining', () => {
    // Boundary: exactly 0 is EXPIRED
    expect(getDeadlineState(0)).toBe('EXPIRED');
    expect(getDeadlineState(-10)).toBe('EXPIRED');
  });

  it('formats countdown string correctly', () => {
    expect(formatCountdown(3665).formatted).toBe('1h 1m 5s');
    expect(formatCountdown(72 * 3600).formatted).toBe('72h 0m 0s');
    expect(formatCountdown(0).formatted).toBe('0h 0m 0s');
    expect(formatCountdown(-5).formatted).toBe('0h 0m 0s');
  });

  it('calculates server offset accurately', () => {
    const fakeServerTime = new Date(Date.now() + 5000).toISOString();
    const offset = calculateServerOffset(fakeServerTime);
    // Offset should be roughly +5000ms
    expect(offset).toBeGreaterThan(4500);
    expect(offset).toBeLessThan(5500);
  });
});
