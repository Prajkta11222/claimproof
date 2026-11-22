export type DeadlineState = 'ACTIVE' | 'URGENT' | 'CRITICAL' | 'EXPIRED';

export type IncidentType =
  | 'hailstorm'
  | 'inundation_flood'
  | 'landslide'
  | 'cloudburst'
  | 'natural_fire'
  | 'unseasonal_rain_post_harvest'
  | 'other';

export type CropSeason = 'kharif' | 'rabi' | 'zaid' | 'other';

export type IntimationChannel =
  | 'crop_insurance_app'
  | 'helpline_14447'
  | 'insurer'
  | 'bank'
  | 'agri_department'
  | 'csc'
  | 'other';

export interface LocationInput {
  lat: number;
  lng: number;
  accuracy_m?: number | null;
}

export interface DeadlineResponse {
  deadline_at: string;
  server_time: string;
  seconds_remaining: number;
  state: DeadlineState;
  rule: string;
  assumptions: string[];
}

export interface PhotoCountsResponse {
  total: number;
  passed: number;
  warn: number;
  fail: number;
}

export interface ChecklistSummaryResponse {
  critical_missing: number;
  warnings: number;
  ok: number;
}

export interface ChecklistItem {
  code: string;
  severity: 'critical' | 'required' | 'recommended';
  status: 'ok' | 'missing' | 'warn';
  label: string;
  hint: string;
  action?: { type: string };
}

export interface ChecklistResponse {
  items: ChecklistItem[];
  completeness: 'complete' | 'incomplete';
}

export interface QcCheck {
  code: string;
  status: 'pass' | 'warn' | 'fail';
  value?: unknown;
  message: string;
}

export interface Photo {
  id: string;
  incident_id: string;
  user_id: string;
  sha256: string;
  source: 'camera_capture' | 'gallery_upload';
  shot_type: 'wide' | 'close_up' | 'document' | 'other';
  width_px: number;
  height_px: number;
  size_bytes: number;
  mime_type: string;
  has_exif: boolean;
  effective_taken_at: string;
  time_basis: 'exif' | 'client' | 'upload';
  gps_basis?: 'exif' | 'client' | null;
  distance_from_plot_m?: number | null;
  qc_status: 'pending' | 'pass' | 'warn' | 'fail';
  qc_checks: QcCheck[];
  ai_status: 'pending' | 'done' | 'failed' | 'skipped';
  ai_attempts: number;
  ai_result?: Record<string, unknown> | null;
  uploaded_at: string;
  created_at: string;
  urls: {
    thumb: string;
    display: string;
    expires_at?: string | null;
  };
}

export interface WeatherSnapshot {
  id: string;
  incident_id: string;
  endpoint: 'forecast' | 'archive';
  summary: {
    window: { start: string; end: string };
    total_precip_mm: number;
    max_hourly_precip_mm: number;
    max_gust_kmh: number;
    temp_min_c?: number | null;
    temp_max_c?: number | null;
    hail_code_hours: number;
    daily: Array<{ date: string; precip_mm: number; max_gust_kmh: number }>;
  };
  fetched_at: string;
}

export interface Report {
  id: string;
  version: number;
  generated_at: string;
  completeness: 'complete' | 'incomplete';
  photo_count: number;
  size_bytes: number;
  sha256: string;
  download?: { url: string; expires_at: string };
}

export interface IntimationBrief {
  id: string;
  channel: IntimationChannel;
  intimated_at: string;
  reference_number?: string | null;
  within_deadline: boolean;
}

export interface Incident {
  id: string;
  user_id: string;
  scheme: 'PMFBY' | 'OTHER';
  status: 'open' | 'archived';
  incident_type: IncidentType;
  description?: string | null;
  event_occurred_at: string;
  event_time_precision: 'exact' | 'date_only';
  deadline_hours: number;
  reporting_deadline_at: string;
  crop_name: string;
  crop_season?: CropSeason | null;
  survey_number?: string | null;
  area_affected_acres?: number | null;
  policy_reference?: string | null;
  location_lat: number;
  location_lng: number;
  location_accuracy_m?: number | null;
  village?: string | null;
  taluka?: string | null;
  district: string;
  state: string;
  created_at: string;
  updated_at: string;
  deadline?: DeadlineResponse | null;
  photo_counts: PhotoCountsResponse;
  checklist_summary: ChecklistSummaryResponse;
  intimations: IntimationBrief[];
}

export interface IncidentListItem {
  id: string;
  status: 'open' | 'archived';
  incident_type: IncidentType;
  crop_name: string;
  district: string;
  state: string;
  event_occurred_at: string;
  created_at: string;
  deadline?: DeadlineResponse | null;
}

export interface IncidentCreateRequest {
  scheme?: 'PMFBY' | 'OTHER';
  incident_type: IncidentType;
  event_occurred_at: string;
  event_time_precision: 'exact' | 'date_only';
  description?: string | null;
  crop_name: string;
  crop_season?: CropSeason | null;
  survey_number?: string | null;
  area_affected_acres?: number | null;
  policy_reference?: string | null;
  location: LocationInput;
  village?: string | null;
  taluka?: string | null;
  district: string;
  state: string;
}

export interface IncidentUpdateRequest {
  status?: 'open' | 'archived';
  incident_type?: IncidentType;
  event_occurred_at?: string;
  event_time_precision?: 'exact' | 'date_only';
  description?: string | null;
  crop_name?: string;
  crop_season?: CropSeason | null;
  survey_number?: string | null;
  area_affected_acres?: number | null;
  policy_reference?: string | null;
  location?: LocationInput;
  village?: string | null;
  taluka?: string | null;
  district?: string;
  state?: string;
}

export interface Intimation {
  id: string;
  incident_id: string;
  channel: IntimationChannel;
  intimated_at: string;
  reference_number?: string | null;
  notes?: string | null;
  recorded_at: string;
  created_at: string;
  within_deadline: boolean;
}

export interface IntimationCreateRequest {
  channel: IntimationChannel;
  intimated_at: string;
  reference_number?: string | null;
  notes?: string | null;
}

export interface Profile {
  id: string;
  full_name: string;
  preferred_language: 'en' | 'mr' | 'hi';
  consent_version?: string | null;
  consent_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdateRequest {
  full_name?: string;
  preferred_language?: 'en' | 'mr' | 'hi';
  consent_version?: string;
}

export interface ApiErrorDetail {
  field?: string;
  issue?: string;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[];
    request_id?: string;
  };
}
