import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { api } from '../../lib/api';
import { toISTString } from '../../lib/time';
import { CountdownCard } from '../../components/CountdownCard';
import { IntimationForm } from '../intimations/IntimationForm';
import { PhotoEvidence } from './PhotoEvidence';
import {
  PhoneCall,
  ExternalLink,
  Camera,
  ClipboardList,
  FileText,
  Trash2,
  CheckCircle2,
  MapPin,
  Calendar,
  AlertCircle,
  Download,
  CloudSun,
} from 'lucide-react';

export function IncidentDashboard() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [showIntimationForm, setShowIntimationForm] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const { data: incident, isLoading, error } = useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.getIncident(id!),
    enabled: !!id,
  });

  const { data: checklist } = useQuery({
    queryKey: ['checklist', id],
    queryFn: () => api.getChecklist(id!),
    enabled: !!id,
  });

  const { data: weather } = useQuery({
    queryKey: ['weather', id],
    queryFn: () => api.getWeather(id!),
    enabled: !!id,
  });

  const { data: reports } = useQuery({
    queryKey: ['reports', id],
    queryFn: () => api.listReports(id!),
    enabled: !!id,
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteIncident(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      navigate('/');
    },
  });

  const weatherMutation = useMutation({
    mutationFn: () => api.refreshWeather(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['weather', id] });
      queryClient.invalidateQueries({ queryKey: ['checklist', id] });
    },
  });

  const reportMutation = useMutation({
    mutationFn: () => api.createReport(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', id] });
    },
  });

  const downloadLatestReport = async () => {
    const latest = reports?.[0];
    if (!latest) return;
    const delivery = await api.downloadReport(latest.id);
    if (!delivery.url) return;
    window.open(delivery.url, '_blank', 'noopener,noreferrer');
  };

  if (isLoading) {
    return (
      <div className="py-20 text-center text-gray-500 text-sm">
        <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
        {t('common.loading')}
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="p-5 bg-red-50 rounded-2xl border border-red-200 text-center text-xs text-red-700">
        <p>{t('common.error')}</p>
        <button
          onClick={() => navigate('/')}
          className="mt-3 px-3 py-1.5 bg-red-600 text-white rounded-xl text-xs font-medium"
        >
          {t('common.back')}
        </button>
      </div>
    );
  }

  const hasIntimation = incident.intimations && incident.intimations.length > 0;

  return (
    <div className="space-y-5">
      {/* Top Incident Summary */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-gray-200/90 shadow-xs">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wide">
              {t(`incident.types.${incident.incident_type}`)}
            </span>
            <h1 className="text-xl font-bold text-gray-900 mt-0.5">
              {incident.crop_name}
            </h1>
          </div>
          <button
            onClick={() => setDeleteConfirmOpen(true)}
            title={t('incident.deleteButton')}
            className="min-h-[40px] min-w-[40px] p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors inline-flex items-center justify-center"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-y-2 gap-x-3 text-xs text-gray-600 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <span>{incident.district}, {incident.state}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <span>{toISTString(incident.event_occurred_at)}</span>
          </div>
          {incident.survey_number && (
            <div>
              <span className="text-gray-400">Gat: </span>
              <span className="font-medium text-gray-800">{incident.survey_number}</span>
            </div>
          )}
          {incident.area_affected_acres && (
            <div>
              <span className="text-gray-400">Area: </span>
              <span className="font-medium text-gray-800">{incident.area_affected_acres} acres</span>
            </div>
          )}
        </div>
      </div>

      {/* 72h Countdown Card (SPEC 8) */}
      {incident.deadline && <CountdownCard deadline={incident.deadline} />}

      {/* STEP A: Official Intimation Card (V1, V3) */}
      <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
              hasIntimation ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'
            }`}>
              A
            </div>
            <h2 className="text-sm font-bold text-gray-900">
              {t('intimation.stepATitle')}
            </h2>
          </div>
          {hasIntimation && (
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <CheckCircle2 className="w-3 h-3" />
              {t('intimation.recorded')}
            </span>
          )}
        </div>

        <p className="text-xs text-gray-600 leading-relaxed">
          {t('intimation.stepADescription')}
        </p>

        {/* Quick Official Action Buttons */}
        <div className="flex flex-wrap gap-2 pt-1">
          <a
            href="tel:14447"
            className="inline-flex items-center gap-1.5 min-h-[42px] px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors"
          >
            <PhoneCall className="w-3.5 h-3.5" />
            <span>{t('intimation.callHelpline')}</span>
          </a>

          <a
            href="https://pmfby.gov.in"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 min-h-[42px] px-3.5 py-2 bg-gray-50 hover:bg-gray-100 text-gray-800 border border-gray-200 rounded-xl text-xs font-semibold transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
            <span>{t('intimation.openPmfby')}</span>
          </a>

          {!showIntimationForm && (
            <button
              onClick={() => setShowIntimationForm(true)}
              className="inline-flex items-center gap-1.5 min-h-[42px] px-3.5 py-2 bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 rounded-xl text-xs font-semibold transition-colors ml-auto"
            >
              <span>{t('intimation.recordButton')}</span>
            </button>
          )}
        </div>

        {/* Intimation Form Inline Drawer */}
        {showIntimationForm && (
          <div className="pt-2">
            <IntimationForm
              incidentId={incident.id}
              onSuccess={() => setShowIntimationForm(false)}
              onCancel={() => setShowIntimationForm(false)}
            />
          </div>
        )}

        {/* Recorded intimations list */}
        {hasIntimation && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
            {incident.intimations.map((item) => (
              <div
                key={item.id}
                className="bg-gray-50/80 p-3 rounded-xl border border-gray-200/80 text-xs flex items-center justify-between gap-2"
              >
                <div>
                  <div className="font-semibold text-gray-900">
                    {t(`intimation.channels.${item.channel}`)}
                  </div>
                  <div className="text-[11px] text-gray-500">
                    {toISTString(item.intimated_at)}
                    {item.reference_number && ` • Ref: ${item.reference_number}`}
                  </div>
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    item.within_deadline
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {item.within_deadline
                    ? t('intimation.withinDeadline')
                    : t('intimation.afterDeadline')}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Step B, C, D */}
      <div className="space-y-2.5">
        {/* Step B */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-4 shadow-xs">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-6 h-6 rounded-full bg-gray-100 text-gray-700 flex items-center justify-center text-xs font-bold">
              B
            </div>
            <Camera className="w-4 h-4 text-gray-500" />
            <h3 className="text-xs font-bold text-gray-800">{t('dashboard.stepB')}</h3>
            <span className="text-[10px] font-semibold bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full ml-auto">
              {incident.photo_counts?.total ?? 0} / 12
            </span>
          </div>
          <div className="mt-3">
            <PhotoEvidence
              incidentId={incident.id}
            />
          </div>
        </div>

        {/* Step C */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-4 shadow-xs">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-6 h-6 rounded-full bg-gray-100 text-gray-700 flex items-center justify-center text-xs font-bold">
              C
            </div>
            <ClipboardList className="w-4 h-4 text-gray-500" />
            <h3 className="text-xs font-bold text-gray-800">{t('dashboard.stepC')}</h3>
            {checklist && (
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ml-auto ${
                checklist.completeness === 'complete'
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {checklist.completeness === 'complete'
                  ? t('dashboard.checklistComplete')
                  : t('dashboard.checklistNeedsAttention')}
              </span>
            )}
          </div>
          {checklist ? (
            <div className="ml-8 mt-3 space-y-2">
              {checklist.items
                .filter((item) => item.status !== 'ok')
                .slice(0, 5)
                .map((item) => (
                  <div key={item.code} className="flex items-start gap-2 text-[11px]">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="font-semibold text-gray-800">{item.label}</p>
                      <p className="text-gray-500">{item.hint}</p>
                    </div>
                  </div>
                ))}
              {checklist.items.every((item) => item.status === 'ok') && (
                <p className="text-[11px] text-emerald-700">{t('dashboard.checklistReady')}</p>
              )}
            </div>
          ) : (
            <p className="text-[11px] text-gray-500 ml-8">{t('dashboard.stepCDesc')}</p>
          )}
        </div>

        {/* Step D */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-4 shadow-xs">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-6 h-6 rounded-full bg-gray-100 text-gray-700 flex items-center justify-center text-xs font-bold">
              D
            </div>
            <FileText className="w-4 h-4 text-gray-500" />
            <h3 className="text-xs font-bold text-gray-800">{t('dashboard.stepD')}</h3>
            <span className="text-[10px] font-semibold bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full ml-auto">
              {reports?.[0] ? `v${reports[0].version}` : t('dashboard.notGenerated')}
            </span>
          </div>
          <div className="ml-8 mt-3 space-y-3">
            <p className="text-[11px] text-gray-500">{t('dashboard.stepDDesc')}</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={weatherMutation.isPending}
                onClick={() => weatherMutation.mutate()}
                className="min-h-[42px] inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-gray-300 bg-white text-xs font-semibold text-gray-700 disabled:opacity-50"
              >
                <CloudSun className="w-4 h-4" />
                {weatherMutation.isPending ? t('common.loading') : t('dashboard.refreshWeather')}
              </button>
              <button
                type="button"
                disabled={reportMutation.isPending}
                onClick={() => reportMutation.mutate()}
                className="min-h-[42px] inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold disabled:opacity-50"
              >
                <FileText className="w-4 h-4" />
                {reportMutation.isPending ? t('common.loading') : t('dashboard.generateReport')}
              </button>
              {reports?.[0] && (
                <button
                  type="button"
                  onClick={() => void downloadLatestReport()}
                  className="min-h-[42px] inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-emerald-300 bg-emerald-50 text-emerald-800 text-xs font-semibold"
                >
                  <Download className="w-4 h-4" />
                  {t('dashboard.downloadReport')}
                </button>
              )}
            </div>
            {weather?.snapshot?.summary && (
              <p className="text-[11px] text-gray-600">
                {t('dashboard.weatherSummary', {
                  precip: weather.snapshot.summary.total_precip_mm,
                  gust: weather.snapshot.summary.max_gust_kmh,
                })}
              </p>
            )}
            {reports?.[0] && (
              <p className="text-[11px] text-gray-500">
                {t('dashboard.latestReport')} v{reports[0].version}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-xl border border-gray-200">
            <div className="flex items-center gap-2 text-red-600">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <h3 className="text-sm font-bold text-gray-900">
                {t('incident.deleteButton')}
              </h3>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              {t('incident.deleteConfirm')}
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDeleteConfirmOpen(false)}
                className="min-h-[40px] px-3.5 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 rounded-lg"
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate()}
                className="min-h-[40px] px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? t('common.loading') : t('common.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
