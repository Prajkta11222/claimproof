import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { IntimationChannel } from '../../types/api';
import { Check, X, ShieldAlert } from 'lucide-react';

const channels: IntimationChannel[] = [
  'crop_insurance_app',
  'helpline_14447',
  'insurer',
  'bank',
  'agri_department',
  'csc',
  'other',
];

interface IntimationFormProps {
  incidentId: string;
  onSuccess: () => void;
  onCancel: () => void;
}

export function IntimationForm({ incidentId, onSuccess, onCancel }: IntimationFormProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [nowString] = useState(() => new Date().toISOString().substring(0, 16));
  const [channel, setChannel] = useState<IntimationChannel>('helpline_14447');
  const [intimatedAt, setIntimatedAt] = useState<string>(nowString);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      api.createIntimation(incidentId, {
        channel,
        intimated_at: new Date(intimatedAt).toISOString(),
        reference_number: referenceNumber.trim() || null,
        notes: notes.trim() || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      onSuccess();
    },
    onError: (err: any) => {
      setError(err?.message || t('common.error'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    mutation.mutate();
  };

  return (
    <div className="bg-emerald-50/70 border border-emerald-200 rounded-2xl p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-gray-900">
          {t('intimation.title')}
        </h3>
        <button
          type="button"
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-700 min-h-[36px] min-w-[36px] inline-flex items-center justify-center rounded-lg"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <p className="text-xs text-gray-600 leading-relaxed bg-white/80 p-2.5 rounded-xl border border-emerald-100">
        {t('intimation.guidance')}
      </p>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            {t('intimation.channelLabel')}
          </label>
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value as IntimationChannel)}
            className="w-full px-3 py-2 rounded-xl border border-gray-300 text-xs bg-white focus:ring-2 focus:ring-emerald-500"
          >
            {channels.map((ch) => (
              <option key={ch} value={ch}>
                {t(`intimation.channels.${ch}`)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            {t('intimation.intimatedAt')}
          </label>
          <input
            type="datetime-local"
            required
            value={intimatedAt}
            onChange={(e) => setIntimatedAt(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-300 text-xs bg-white focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            {t('intimation.referenceNumber')}
          </label>
          <input
            type="text"
            placeholder="e.g. 14447 SMS ticket number"
            value={referenceNumber}
            onChange={(e) => setReferenceNumber(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-300 text-xs bg-white focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            {t('intimation.notes')}
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 rounded-xl border border-gray-300 text-xs bg-white focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div className="pt-2 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="min-h-[40px] px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 rounded-lg"
          >
            {t('common.cancel')}
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="min-h-[40px] px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-xs transition-colors inline-flex items-center gap-1.5 disabled:opacity-50"
          >
            <Check className="w-4 h-4" />
            <span>{mutation.isPending ? t('common.loading') : t('common.save')}</span>
          </button>
        </div>
      </form>
    </div>
  );
}
