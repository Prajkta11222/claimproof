import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { api } from '../../lib/api';
import type { IncidentType, CropSeason } from '../../types/api';
import { Navigation, ArrowLeft, ArrowRight, Check } from 'lucide-react';

const incidentTypes = [
  'hailstorm',
  'inundation_flood',
  'landslide',
  'cloudburst',
  'natural_fire',
  'unseasonal_rain_post_harvest',
  'other',
] as const;

const cropSeasons = ['kharif', 'rabi', 'zaid', 'other'] as const;

export interface IncidentFormValues {
  incident_type: IncidentType;
  event_date: string;
  event_time?: string;
  description?: string;
  location_lat: number;
  location_lng: number;
  location_accuracy_m?: number;
  village?: string;
  taluka?: string;
  district: string;
  state: string;
  crop_name: string;
  crop_season?: CropSeason;
  survey_number?: string;
  area_affected_acres?: number;
  policy_reference?: string;
}

export function NewIncidentPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [dateOnly, setDateOnly] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locError, setLocError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const schema = z.object({
    incident_type: z.enum(incidentTypes),
    event_date: z.string().min(1, t('validation.required')),
    event_time: z.string().optional(),
    description: z.string().max(1000).optional(),

    location_lat: z.coerce.number().min(-90).max(90),
    location_lng: z.coerce.number().min(-180).max(180),
    location_accuracy_m: z.coerce.number().optional(),
    village: z.string().max(80).optional(),
    taluka: z.string().max(80).optional(),
    district: z.string().min(1, t('validation.required')).max(80),
    state: z.string().min(1, t('validation.required')).max(80),

    crop_name: z.string().min(1, t('validation.required')).max(60),
    crop_season: z.enum(cropSeasons).optional(),
    survey_number: z.string().max(40).optional(),
    area_affected_acres: z.coerce.number().positive().max(10000).optional(),
    policy_reference: z.string().max(40).optional(),
  });

  const [defaultDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [defaultTime] = useState(() => new Date().toTimeString().substring(0, 5));

  const {
    register,
    handleSubmit,
    setValue,
    trigger,
    formState: { errors },
  } = useForm<IncidentFormValues>({
    resolver: zodResolver(schema) as any,
    defaultValues: {
      incident_type: 'hailstorm',
      event_date: defaultDate,
      event_time: defaultTime,
      state: 'Maharashtra',
      district: '',
      crop_name: '',
    },
  });

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setLocError(t('incident.form.locationDenied'));
      return;
    }
    setLocating(true);
    setLocError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setValue('location_lat', Number(pos.coords.latitude.toFixed(6)));
        setValue('location_lng', Number(pos.coords.longitude.toFixed(6)));
        if (pos.coords.accuracy) {
          setValue('location_accuracy_m', Math.round(pos.coords.accuracy));
        }
        setLocating(false);
      },
      () => {
        setLocError(t('incident.form.locationDenied'));
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const nextStep = async () => {
    let valid = false;
    if (step === 1) {
      valid = await trigger(['incident_type', 'event_date', 'event_time', 'description']);
    } else if (step === 2) {
      valid = await trigger(['location_lat', 'location_lng', 'district', 'state', 'village', 'taluka']);
    }
    if (valid) {
      setStep((prev) => (prev + 1) as 2 | 3);
    }
  };

  const prevStep = () => {
    setStep((prev) => (prev - 1) as 1 | 2);
  };

  const onSubmit = async (data: IncidentFormValues) => {
    setSubmitting(true);
    setSubmitError(null);

    try {
      const precision = dateOnly ? 'date_only' : 'exact';
      const eventOccurredAt = dateOnly
        ? `${data.event_date}T00:00:00+05:30`
        : `${data.event_date}T${data.event_time || '00:00'}:00+05:30`;

      const incident = await api.createIncident({
        scheme: 'PMFBY',
        incident_type: data.incident_type,
        event_occurred_at: eventOccurredAt,
        event_time_precision: precision,
        description: data.description || null,
        crop_name: data.crop_name,
        crop_season: data.crop_season || null,
        survey_number: data.survey_number || null,
        area_affected_acres: data.area_affected_acres ? Number(data.area_affected_acres) : null,
        policy_reference: data.policy_reference || null,
        location: {
          lat: data.location_lat,
          lng: data.location_lng,
          accuracy_m: data.location_accuracy_m || null,
        },
        village: data.village || null,
        taluka: data.taluka || null,
        district: data.district,
        state: data.state,
      });

      navigate(`/incidents/${incident.id}`);
    } catch (err: any) {
      setSubmitError(err?.message || t('common.error'));
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Stepper Progress */}
      <div>
        <div className="flex items-center justify-between text-xs font-semibold text-gray-500 mb-2">
          <span>{t(`incident.steps.${step === 1 ? 'typeAndTime' : step === 2 ? 'location' : 'cropAndPlot'}`)}</span>
          <span>{step} / 3</span>
        </div>
        <div className="grid grid-cols-3 gap-1.5">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1.5 rounded-full transition-colors ${
                s <= step ? 'bg-emerald-600' : 'bg-gray-200'
              }`}
            />
          ))}
        </div>
      </div>

      {submitError && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs">
          {submitError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs space-y-4">
        {/* STEP 1: Type & Time */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('incident.form.incidentType')}
              </label>
              <select
                {...register('incident_type')}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
              >
                {incidentTypes.map((type) => (
                  <option key={type} value={type}>
                    {t(`incident.types.${type}`)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('incident.form.eventTime')}
              </label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  {...register('event_date')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
                {!dateOnly && (
                  <input
                    type="time"
                    {...register('event_time')}
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                  />
                )}
              </div>
            </div>

            <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-gray-700">
                <input
                  type="checkbox"
                  checked={dateOnly}
                  onChange={(e) => setDateOnly(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                />
                <span>{t('incident.form.dateOnly')}</span>
              </label>
              {dateOnly && (
                <p className="text-[11px] text-amber-800 mt-2 leading-relaxed">
                  {t('incident.form.dateOnlyHint')}
                </p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('incident.form.description')}
              </label>
              <textarea
                {...register('description')}
                rows={3}
                placeholder={t('incident.form.descriptionPlaceholder')}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>
        )}

        {/* STEP 2: Location */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <button
                type="button"
                onClick={handleGetLocation}
                disabled={locating}
                className="w-full min-h-[44px] inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-semibold transition-colors disabled:opacity-50"
              >
                <Navigation className="w-4 h-4 text-emerald-600" />
                <span>{locating ? t('incident.form.locationFetching') : t('incident.form.useMyLocation')}</span>
              </button>
              {locError && <p className="text-xs text-red-600 mt-1">{locError}</p>}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.latitude')}
                </label>
                <input
                  type="number"
                  step="any"
                  placeholder="21.1458"
                  {...register('location_lat')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
                {errors.location_lat && <p className="text-xs text-red-600 mt-0.5">{errors.location_lat.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.longitude')}
                </label>
                <input
                  type="number"
                  step="any"
                  placeholder="79.0882"
                  {...register('location_lng')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
                {errors.location_lng && <p className="text-xs text-red-600 mt-0.5">{errors.location_lng.message}</p>}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.district')}
                </label>
                <input
                  type="text"
                  placeholder="e.g., Nagpur"
                  {...register('district')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
                {errors.district && <p className="text-xs text-red-600 mt-0.5">{errors.district.message}</p>}
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.state')}
                </label>
                <input
                  type="text"
                  {...register('state')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.village')}
                </label>
                <input
                  type="text"
                  {...register('village')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.taluka')}
                </label>
                <input
                  type="text"
                  {...register('taluka')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Crop & Plot */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('incident.form.cropName')} *
              </label>
              <input
                type="text"
                placeholder={t('incident.form.cropNamePlaceholder')}
                {...register('crop_name')}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
              />
              {errors.crop_name && <p className="text-xs text-red-600 mt-0.5">{errors.crop_name.message}</p>}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.cropSeason')}
                </label>
                <select
                  {...register('crop_season')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">{t('incident.form.selectSeason')}</option>
                  {cropSeasons.map((season) => (
                    <option key={season} value={season}>
                      {t(`incident.seasons.${season}`)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  {t('incident.form.areaAffected')}
                </label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g., 2.5"
                  {...register('area_affected_acres')}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('incident.form.surveyNumber')}
              </label>
              <input
                type="text"
                placeholder={t('incident.form.surveyNumberPlaceholder')}
                {...register('survey_number')}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                {t('incident.form.policyReference')}
              </label>
              <input
                type="text"
                placeholder="PMFBY-2026-XXXX"
                {...register('policy_reference')}
                className="w-full px-3 py-2.5 rounded-xl border border-gray-300 text-sm focus:ring-2 focus:ring-emerald-500"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                {t('incident.form.policyReferenceHint')}
              </p>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="pt-3 border-t border-gray-100 flex items-center justify-between gap-2">
          {step > 1 ? (
            <button
              type="button"
              onClick={prevStep}
              className="min-h-[44px] px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-100 rounded-xl transition-colors inline-flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{t('common.back')}</span>
            </button>
          ) : (
            <div />
          )}

          {step < 3 ? (
            <button
              type="button"
              onClick={nextStep}
              className="min-h-[44px] px-5 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-xs transition-colors inline-flex items-center gap-1.5 ml-auto"
            >
              <span>{t('common.next')}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={submitting}
              className="min-h-[44px] px-6 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-xs transition-colors inline-flex items-center gap-1.5 ml-auto disabled:opacity-50"
            >
              {submitting ? (
                <span>{t('common.loading')}</span>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>{t('common.submit')}</span>
                </>
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
