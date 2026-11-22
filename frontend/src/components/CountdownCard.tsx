import React, { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Clock, AlertTriangle, AlertOctagon, CheckCircle2 } from 'lucide-react';
import type { DeadlineResponse, DeadlineState } from '../types/api';
import {
  calculateServerOffset,
  formatCountdown,
  getDeadlineState,
  getSecondsRemaining,
} from '../lib/time';

interface CountdownCardProps {
  deadline: DeadlineResponse;
}

export function CountdownCard({ deadline }: CountdownCardProps) {
  const { t } = useTranslation();

  // Server offset calculated once at mount from server_time (SPEC 8.4)
  const serverOffsetMs = useMemo(() => {
    return calculateServerOffset(deadline.server_time);
  }, [deadline.server_time]);

  const [secondsRemaining, setSecondsRemaining] = useState<number>(() =>
    getSecondsRemaining(deadline.deadline_at, serverOffsetMs)
  );

  useEffect(() => {
    const update = () => {
      setSecondsRemaining(getSecondsRemaining(deadline.deadline_at, serverOffsetMs));
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [deadline.deadline_at, serverOffsetMs]);

  const state: DeadlineState = getDeadlineState(secondsRemaining);
  const countdown = formatCountdown(secondsRemaining);

  const config = {
    ACTIVE: {
      border: 'border-emerald-200',
      bg: 'bg-emerald-50/70',
      text: 'text-emerald-900',
      accent: 'text-emerald-600',
      badgeBg: 'bg-emerald-100',
      badgeText: 'text-emerald-800',
      icon: CheckCircle2,
      bannerText: t('deadline.active'),
    },
    URGENT: {
      border: 'border-amber-300',
      bg: 'bg-amber-50/80',
      text: 'text-amber-950',
      accent: 'text-amber-600',
      badgeBg: 'bg-amber-100',
      badgeText: 'text-amber-800',
      icon: AlertTriangle,
      bannerText: t('deadline.urgent'),
    },
    CRITICAL: {
      border: 'border-red-300',
      bg: 'bg-red-50/90',
      text: 'text-red-950',
      accent: 'text-red-600',
      badgeBg: 'bg-red-100',
      badgeText: 'text-red-800',
      icon: AlertOctagon,
      bannerText: t('deadline.critical'),
    },
    EXPIRED: {
      border: 'border-gray-200',
      bg: 'bg-gray-50',
      text: 'text-gray-800',
      accent: 'text-gray-500',
      badgeBg: 'bg-gray-200',
      badgeText: 'text-gray-700',
      icon: Clock,
      bannerText: t('deadline.expired'),
    },
  }[state];

  const Icon = config.icon;

  return (
    <div
      className={`rounded-2xl border p-5 ${config.border} ${config.bg} shadow-xs transition-colors`}
    >
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Icon className={`w-5 h-5 shrink-0 ${config.accent}`} />
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            {t('deadline.title', 'Reporting Countdown')}
          </span>
        </div>
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${config.badgeBg} ${config.badgeText}`}
        >
          {t(`deadline.states.${state}`)}
        </span>
      </div>

      <div className="space-y-2">
        {state !== 'EXPIRED' ? (
          <div>
            <div className="text-3xl font-extrabold tracking-tight font-mono text-gray-900">
              {countdown.formatted}
            </div>
            <p className="text-xs text-gray-600 mt-1">{config.bannerText}</p>
          </div>
        ) : (
          <p className="text-xs text-gray-700 leading-relaxed font-medium">
            {config.bannerText}
          </p>
        )}
      </div>

      <p className="text-[11px] text-gray-500 mt-3 pt-3 border-t border-gray-200/60 leading-normal">
        {t('deadline.rulesNote')}
      </p>
    </div>
  );
}
