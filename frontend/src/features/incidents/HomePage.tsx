import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../../lib/api';
import { toISTString, getDeadlineState } from '../../lib/time';
import { Plus, AlertTriangle, AlertOctagon, ChevronRight, Sprout, MapPin, Calendar } from 'lucide-react';
import type { IncidentListItem } from '../../types/api';

export function HomePage() {
  const { t } = useTranslation();

  const { data: incidents, isLoading, error, refetch } = useQuery({
    queryKey: ['incidents'],
    queryFn: api.listIncidents,
  });

  const criticalCount = incidents?.filter(
    (inc) => inc.deadline && getDeadlineState(inc.deadline.seconds_remaining) === 'CRITICAL'
  ).length || 0;

  const urgentCount = incidents?.filter(
    (inc) => inc.deadline && getDeadlineState(inc.deadline.seconds_remaining) === 'URGENT'
  ).length || 0;

  return (
    <div className="space-y-5">
      {/* Urgent/Critical Banners (SPEC 8.3) */}
      {criticalCount > 0 && (
        <div className="bg-red-50 border-l-4 border-red-500 p-3.5 rounded-r-xl shadow-xs flex items-center gap-2.5 text-red-900 text-xs font-semibold">
          <AlertOctagon className="w-5 h-5 text-red-600 shrink-0" />
          <span>{t('home.criticalBanner')}</span>
        </div>
      )}

      {urgentCount > 0 && criticalCount === 0 && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-3.5 rounded-r-xl shadow-xs flex items-center gap-2.5 text-amber-900 text-xs font-semibold">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
          <span>{t('home.urgentBanner')}</span>
        </div>
      )}

      {/* Main Action Header */}
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{t('home.title')}</h1>
          <p className="text-xs text-gray-500 mt-0.5">PMFBY 72h evidence tracker</p>
        </div>
        <Link
          to="/incidents/new"
          className="inline-flex items-center gap-1.5 min-h-[44px] px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>{t('home.reportNewLoss')}</span>
        </Link>
      </div>

      {/* Incidents List */}
      {isLoading ? (
        <div className="py-16 text-center text-gray-500 text-sm">
          <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          {t('common.loading')}
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 rounded-2xl border border-red-200 text-center text-xs text-red-700 space-y-2">
          <p>{t('common.error')}</p>
          <button
            onClick={() => refetch()}
            className="px-3 py-1 bg-red-600 text-white rounded-lg text-xs font-medium"
          >
            {t('common.retry')}
          </button>
        </div>
      ) : !incidents || incidents.length === 0 ? (
        <div className="bg-white border border-dashed border-gray-300 rounded-2xl p-10 text-center">
          <div className="w-12 h-12 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 mx-auto mb-3">
            <Sprout className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            {t('home.noIncidents')}
          </h3>
          <p className="text-xs text-gray-500 max-w-xs mx-auto mb-4">
            Record a loss event as soon as possible to start your 72-hour timeline and collect evidence.
          </p>
          <Link
            to="/incidents/new"
            className="inline-flex items-center gap-1.5 min-h-[44px] px-4 py-2 bg-emerald-600 text-white text-xs font-semibold rounded-xl hover:bg-emerald-700 shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>{t('home.reportNewLoss')}</span>
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((incident) => (
            <IncidentCard key={incident.id} incident={incident} />
          ))}
        </div>
      )}
    </div>
  );
}

function IncidentCard({ incident }: { incident: IncidentListItem }) {
  const { t } = useTranslation();

  const deadline = incident.deadline;
  const state = deadline ? getDeadlineState(deadline.seconds_remaining) : 'ACTIVE';

  const badgeStyle = {
    ACTIVE: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    URGENT: 'bg-amber-50 text-amber-800 border-amber-200',
    CRITICAL: 'bg-red-50 text-red-800 border-red-200',
    EXPIRED: 'bg-gray-100 text-gray-700 border-gray-200',
  }[state];

  return (
    <Link
      to={`/incidents/${incident.id}`}
      className="block bg-white rounded-2xl border border-gray-200/90 p-4 hover:border-emerald-300 hover:shadow-xs transition-all group"
    >
      <div className="flex items-start justify-between gap-2 mb-2.5">
        <div>
          <span className="text-xs font-medium text-emerald-700 uppercase tracking-wide">
            {t(`incident.types.${incident.incident_type}`)}
          </span>
          <h3 className="text-base font-bold text-gray-900 group-hover:text-emerald-700 transition-colors">
            {incident.crop_name}
          </h3>
        </div>

        {deadline && (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${badgeStyle}`}
          >
            {t(`deadline.states.${state}`)}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-gray-600 pt-2 border-t border-gray-100">
        <div className="flex items-center gap-1">
          <MapPin className="w-3.5 h-3.5 text-gray-400" />
          <span>{incident.district}, {incident.state}</span>
        </div>
        <div className="flex items-center gap-1">
          <Calendar className="w-3.5 h-3.5 text-gray-400" />
          <span>{toISTString(incident.event_occurred_at)}</span>
        </div>
        <ChevronRight className="w-4 h-4 text-gray-400 ml-auto group-hover:translate-x-0.5 transition-transform" />
      </div>
    </Link>
  );
}
