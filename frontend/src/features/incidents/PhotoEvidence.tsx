import React, { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Camera, ImagePlus, Trash2, Upload } from 'lucide-react';
import { api } from '../../lib/api';
import type { Photo } from '../../types/api';

interface Props {
  incidentId: string;
}

export function PhotoEvidence({ incidentId }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const cameraInput = useRef<HTMLInputElement>(null);
  const galleryInput = useRef<HTMLInputElement>(null);
  const [shotType, setShotType] = useState<'wide' | 'close_up' | 'document' | 'other'>('wide');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(false);

  const photosQuery = useQuery({
    queryKey: ['photos', incidentId],
    queryFn: () => api.listPhotos(incidentId),
    refetchInterval: (query) =>
      query.state.data?.some((photo) => photo.ai_status === 'pending') ? 2500 : false,
  });

  const deleteMutation = useMutation({
    mutationFn: (photoId: string) => api.deletePhoto(photoId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['photos', incidentId] }),
        queryClient.invalidateQueries({ queryKey: ['checklist', incidentId] }),
        queryClient.invalidateQueries({ queryKey: ['incident', incidentId] }),
      ]);
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: (photoId: string) => api.analyzePhoto(photoId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['photos', incidentId] }),
        queryClient.invalidateQueries({ queryKey: ['checklist', incidentId] }),
        queryClient.invalidateQueries({ queryKey: ['incident', incidentId] }),
      ]);
    },
  });

  const uploadFile = async (file: File, source: 'camera_capture' | 'gallery_upload') => {
    setUploadError(null);
    setUploadProgress(true);
    try {
      let options: Parameters<typeof api.uploadPhoto>[4] | undefined;
      if (source === 'gallery_upload') {
        options = { clientReportedAt: new Date(file.lastModified).toISOString() };
      } else {
        const position = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            timeout: 10000,
          });
        }).catch(() => null);

        options = {
          clientReportedAt: new Date().toISOString(),
          gpsLat: position?.coords.latitude,
          gpsLng: position?.coords.longitude,
          gpsAccuracy: position ? Math.round(position.coords.accuracy) : undefined,
        };
      }
      await api.uploadPhoto(incidentId, file, source, shotType, options);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['photos', incidentId] }),
        queryClient.invalidateQueries({ queryKey: ['checklist', incidentId] }),
        queryClient.invalidateQueries({ queryKey: ['incident', incidentId] }),
      ]);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('common.error');
      setUploadError(message);
    } finally {
      setUploadProgress(false);
    }
  };

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>, source: 'camera_capture' | 'gallery_upload') => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (file) void uploadFile(file, source);
  };

  const photos = photosQuery.data ?? [];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={uploadProgress}
          onClick={() => cameraInput.current?.click()}
          className="min-h-[44px] inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold disabled:opacity-50"
        >
          <Camera className="w-4 h-4" />
          {t('photos.camera')}
        </button>
        <button
          type="button"
          disabled={uploadProgress}
          onClick={() => galleryInput.current?.click()}
          className="min-h-[44px] inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-white border border-gray-300 text-gray-800 text-xs font-semibold disabled:opacity-50"
        >
          <ImagePlus className="w-4 h-4" />
          {t('photos.gallery')}
        </button>
        <input
          ref={cameraInput}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(event) => onFileChange(event, 'camera_capture')}
        />
        <input
          ref={galleryInput}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(event) => onFileChange(event, 'gallery_upload')}
        />
      </div>

      <label className="block">
        <span className="block text-[11px] font-semibold text-gray-700 mb-1">{t('photos.shotType')}</span>
        <select
          value={shotType}
          onChange={(event) => setShotType(event.target.value as typeof shotType)}
          className="w-full min-h-[42px] rounded-xl border border-gray-300 px-3 text-xs"
        >
          <option value="wide">{t('photos.types.wide')}</option>
          <option value="close_up">{t('photos.types.closeUp')}</option>
          <option value="document">{t('photos.types.document')}</option>
          <option value="other">{t('photos.types.other')}</option>
        </select>
      </label>

      {uploadProgress && (
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <Upload className="w-4 h-4 animate-pulse" />
          {t('photos.uploading')}
        </div>
      )}
      {uploadError && (
        <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {uploadError}
        </div>
      )}

      {photos.length > 0 ? (
        <div className="grid grid-cols-2 gap-2">
          {photos.map((photo) => (
            <PhotoCard
              key={photo.id}
              photo={photo}
              deleting={deleteMutation.isPending && deleteMutation.variables === photo.id}
              onDelete={() => deleteMutation.mutate(photo.id)}
              analyzing={analyzeMutation.isPending && analyzeMutation.variables === photo.id}
              onAnalyze={() => analyzeMutation.mutate(photo.id)}
            />
          ))}
        </div>
      ) : (
        <p className="text-[11px] text-gray-500">{t('photos.empty')}</p>
      )}
    </div>
  );
}

function PhotoCard({ photo, deleting, onDelete, analyzing, onAnalyze }: {
  photo: Photo;
  deleting: boolean;
  onDelete: () => void;
  analyzing: boolean;
  onAnalyze: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden bg-white">
      {photo.urls.thumb ? (
        <img src={photo.urls.thumb} alt="" className="w-full h-28 object-cover" />
      ) : (
        <div className="h-28 bg-gray-100" />
      )}
      <div className="p-2 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className={`text-[10px] font-bold uppercase ${
            photo.qc_status === 'fail'
              ? 'text-red-700'
              : photo.qc_status === 'warn'
                ? 'text-amber-700'
                : 'text-emerald-700'
          }`}>
            {photo.qc_status}
          </span>
          <button
            type="button"
            disabled={deleting}
            onClick={onDelete}
            className="min-h-[32px] min-w-[32px] inline-flex items-center justify-center text-gray-400 hover:text-red-600"
            title={t('photos.delete')}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
        {photo.qc_checks.find((check) => check.status !== 'pass')?.message && (
          <p className="text-[10px] leading-snug text-gray-600">
            {photo.qc_checks.find((check) => check.status !== 'pass')?.message}
          </p>
        )}
        {typeof photo.ai_result?.description === 'string' && (
          <p className="text-[10px] leading-snug text-gray-600">
            {t('photos.aiObservation')}: {photo.ai_result.description}
          </p>
        )}
        {photo.ai_status === 'failed' && photo.ai_attempts < 3 && (
          <button
            type="button"
            disabled={analyzing}
            onClick={onAnalyze}
            className="mt-1 min-h-[32px] w-full rounded-lg border border-amber-300 bg-amber-50 text-[10px] font-semibold text-amber-800"
          >
            {analyzing ? t('photos.retrying') : t('photos.retryAi')}
          </button>
        )}
      </div>
    </div>
  );
}
