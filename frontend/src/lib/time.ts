import type { DeadlineState } from '../types/api';

export function calculateServerOffset(serverTimeIso: string): number {
  const serverMs = new Date(serverTimeIso).getTime();
  const clientMs = Date.now();
  return serverMs - clientMs;
}

export function getAdjustedNow(serverOffsetMs: number): number {
  return Date.now() + serverOffsetMs;
}

export function getSecondsRemaining(deadlineAtIso: string, serverOffsetMs: number = 0): number {
  const deadlineMs = new Date(deadlineAtIso).getTime();
  const adjustedNowMs = getAdjustedNow(serverOffsetMs);
  return Math.max(0, Math.floor((deadlineMs - adjustedNowMs) / 1000));
}

export function getDeadlineState(secondsRemaining: number): DeadlineState {
  if (secondsRemaining <= 0) return 'EXPIRED';
  if (secondsRemaining <= 6 * 3600) return 'CRITICAL';
  if (secondsRemaining <= 24 * 3600) return 'URGENT';
  return 'ACTIVE';
}

export function formatCountdown(totalSeconds: number): {
  hours: number;
  minutes: number;
  seconds: number;
  formatted: string;
} {
  if (totalSeconds <= 0) {
    return { hours: 0, minutes: 0, seconds: 0, formatted: '0h 0m 0s' };
  }
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return {
    hours,
    minutes,
    seconds,
    formatted: `${hours}h ${minutes}m ${seconds}s`,
  };
}

export function toISTString(dateOrIso: string | Date): string {
  const date = typeof dateOrIso === 'string' ? new Date(dateOrIso) : dateOrIso;
  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    dateStyle: 'medium',
    timeStyle: 'short',
    hour12: true,
  }).format(date);
}
