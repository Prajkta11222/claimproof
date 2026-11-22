import { supabase } from './supabase';
import type {
  Incident,
  IncidentCreateRequest,
  IncidentListItem,
  IncidentUpdateRequest,
  Intimation,
  IntimationCreateRequest,
  Profile,
  ProfileUpdateRequest,
  ApiErrorResponse,
  ChecklistResponse,
  Photo,
  WeatherSnapshot,
  Report,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  code: string;
  details?: { field?: string; issue?: string }[];
  requestId?: string;
  status: number;

  constructor(status: number, data: ApiErrorResponse['error']) {
    super(data.message || 'API request failed');
    this.name = 'ApiError';
    this.status = status;
    this.code = data.code || 'UNKNOWN_ERROR';
    this.details = data.details;
    this.requestId = data.request_id;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null as T;
  }

  const json = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, json.error || { code: 'HTTP_ERROR', message: response.statusText });
  }

  return json as T;
}

export const api = {
  // Health
  getHealth: () => request<{ status: string; version: string }>('/health'),

  // Profile
  getProfile: () => request<Profile>('/me'),
  updateProfile: (data: ProfileUpdateRequest) =>
    request<Profile>('/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // Incidents
  listIncidents: () => request<IncidentListItem[]>('/incidents'),
  getIncident: (id: string) => request<Incident>(`/incidents/${id}`),
  createIncident: (data: IncidentCreateRequest) =>
    request<Incident>('/incidents', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateIncident: (id: string, data: IncidentUpdateRequest) =>
    request<Incident>(`/incidents/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteIncident: (id: string) =>
    request<void>(`/incidents/${id}?confirm=true`, {
      method: 'DELETE',
    }),
  getChecklist: (id: string) => request<ChecklistResponse>(`/incidents/${id}/checklist`),
  listPhotos: (incidentId: string) => request<Photo[]>(`/incidents/${incidentId}/photos`),
  uploadPhoto: async (
    incidentId: string,
    file: File,
    source: 'camera_capture' | 'gallery_upload',
    shotType: 'wide' | 'close_up' | 'document' | 'other',
    options?: {
      clientReportedAt?: string;
      gpsLat?: number;
      gpsLng?: number;
      gpsAccuracy?: number;
    },
  ): Promise<Photo> => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    const form = new FormData();
    form.append('file', file);
    form.append('source', source);
    form.append('shot_type', shotType);
    if (options?.clientReportedAt) form.append('client_reported_at', options.clientReportedAt);
    if (options?.gpsLat !== undefined) form.append('client_gps_lat', String(options.gpsLat));
    if (options?.gpsLng !== undefined) form.append('client_gps_lng', String(options.gpsLng));
    if (options?.gpsAccuracy !== undefined) {
      form.append('client_gps_accuracy_m', String(options.gpsAccuracy));
    }

    let lastError: unknown;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const response = await fetch(`${API_BASE}/incidents/${incidentId}/photos`, {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        });
        if (response.status === 204) return null as unknown as Photo;
        const json = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new ApiError(response.status, json.error || {
            code: 'HTTP_ERROR',
            message: response.statusText,
          });
        }
        return json as Photo;
      } catch (error) {
        lastError = error;
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) throw error;
        if (attempt < 2) await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
      }
    }
    throw lastError;
  },
  deletePhoto: (photoId: string) =>
    request<void>(`/photos/${photoId}`, { method: 'DELETE' }),
  updatePhoto: (photoId: string, shotType: 'wide' | 'close_up' | 'document' | 'other') =>
    request<Photo>(`/photos/${photoId}`, {
      method: 'PATCH',
      body: JSON.stringify({ shot_type: shotType }),
    }),
  analyzePhoto: (photoId: string) =>
    request<Photo>(`/photos/${photoId}/analyze`, { method: 'POST' }),
  getWeather: (incidentId: string) =>
    request<{ snapshot: WeatherSnapshot | null }>(`/incidents/${incidentId}/weather`),
  refreshWeather: (incidentId: string) =>
    request<{ status: 'available' | 'unavailable'; snapshot: WeatherSnapshot | null }>(
      `/incidents/${incidentId}/weather/refresh`,
      { method: 'POST' },
    ),
  createReport: (incidentId: string) =>
    request<Report>(`/incidents/${incidentId}/reports`, { method: 'POST' }),
  listReports: (incidentId: string) =>
    request<Report[]>(`/incidents/${incidentId}/reports`),
  downloadReport: (reportId: string) =>
    request<{ url: string; expires_at: string }>(`/reports/${reportId}/download`),

  // Intimations
  listIntimations: (incidentId: string) =>
    request<Intimation[]>(`/incidents/${incidentId}/intimations`),
  createIntimation: (incidentId: string, data: IntimationCreateRequest) =>
    request<Intimation>(`/incidents/${incidentId}/intimations`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteIntimation: (intimationId: string) =>
    request<void>(`/intimations/${intimationId}`, {
      method: 'DELETE',
    }),
};
