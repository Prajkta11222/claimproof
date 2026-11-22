-- ============ helpers ============
create or replace function public.set_updated_at() returns trigger
language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

-- ============ profiles ============
create table if not exists public.profiles (
  id                 uuid primary key references auth.users(id) on delete cascade,
  full_name          text not null check (char_length(full_name) between 1 and 100),
  preferred_language text not null default 'en' check (preferred_language in ('en','mr','hi')),
  consent_version    text,
  consent_at         timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
do $$
begin
  if not exists (
    select 1 from pg_trigger
    where tgname = 'trg_profiles_updated'
      and tgrelid = 'public.profiles'::regclass
  ) then
    create trigger trg_profiles_updated before update on public.profiles
      for each row execute function public.set_updated_at();
  end if;
end $$;

-- ============ incidents ============
create table if not exists public.incidents (
  id                     uuid primary key default gen_random_uuid(),
  user_id                uuid not null references auth.users(id) on delete cascade,
  scheme                 text not null default 'PMFBY' check (scheme in ('PMFBY','OTHER')),
  status                 text not null default 'open' check (status in ('open','archived')),

  incident_type          text not null check (incident_type in
    ('hailstorm','inundation_flood','landslide','cloudburst','natural_fire',
     'unseasonal_rain_post_harvest','other')),
  description            text check (char_length(description) <= 1000),

  event_occurred_at      timestamptz not null,           -- normalised (see deadline rules)
  event_time_precision   text not null check (event_time_precision in ('exact','date_only')),
  deadline_hours         int  not null default 72 check (deadline_hours between 1 and 720),
  reporting_deadline_at  timestamptz not null,           -- computed by API, never by client

  crop_name              text not null check (char_length(crop_name) between 1 and 60),
  crop_season            text check (crop_season in ('kharif','rabi','zaid','other')),
  survey_number          text check (char_length(survey_number) <= 40),
  area_affected_acres    numeric(8,2) check (area_affected_acres > 0 and area_affected_acres <= 10000),
  policy_reference       text check (char_length(policy_reference) <= 40),  -- NOT bank/Aadhaar numbers

  location_lat           numeric(9,6) not null check (location_lat between -90 and 90),
  location_lng           numeric(9,6) not null check (location_lng between -180 and 180),
  location_accuracy_m    numeric(8,1),
  village                text check (char_length(village) <= 80),
  taluka                 text check (char_length(taluka) <= 80),
  district               text not null check (char_length(district) between 1 and 80),
  state                  text not null check (char_length(state) between 1 and 80),

  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);
create index if not exists idx_incidents_user_created on public.incidents (user_id, created_at desc);
do $$
begin
  if not exists (
    select 1 from pg_trigger
    where tgname = 'trg_incidents_updated'
      and tgrelid = 'public.incidents'::regclass
  ) then
    create trigger trg_incidents_updated before update on public.incidents
      for each row execute function public.set_updated_at();
  end if;
end $$;

-- ============ photos ============
create table if not exists public.photos (
  id                    uuid primary key default gen_random_uuid(),
  incident_id           uuid not null references public.incidents(id) on delete cascade,
  user_id               uuid not null references auth.users(id) on delete cascade,

  storage_path_original text not null,
  storage_path_display  text not null,
  storage_path_thumb    text not null,
  original_filename     text,                              -- display only, never used in paths
  mime_type             text not null check (mime_type in ('image/jpeg','image/png','image/webp')),
  size_bytes            int  not null check (size_bytes > 0),
  width_px              int  not null,
  height_px             int  not null,
  sha256                char(64) not null check (sha256 ~ '^[0-9a-f]{64}$'),

  source                text not null check (source in ('camera_capture','gallery_upload')),
  shot_type             text not null default 'other' check (shot_type in ('wide','close_up','document','other')),

  -- time & location evidence
  exif_taken_at         timestamptz,
  exif_gps_lat          numeric(9,6),
  exif_gps_lng          numeric(9,6),
  exif_make             text,
  exif_model            text,
  has_exif              boolean not null default false,
  client_reported_at    timestamptz,                       -- camera: capture event; gallery: file.lastModified
  client_gps_lat        numeric(9,6),                      -- only stored for source='camera_capture'
  client_gps_lng        numeric(9,6),
  client_gps_accuracy_m numeric(8,1),
  effective_taken_at    timestamptz not null,
  time_basis            text not null check (time_basis in ('exif','client','upload')),
  gps_basis             text check (gps_basis in ('exif','client')),
  distance_from_plot_m  numeric(10,1),
  uploaded_at           timestamptz not null default now(),  -- server-trusted time anchor

  -- QC
  qc_status             text not null default 'pending' check (qc_status in ('pending','pass','warn','fail')),
  qc_checks             jsonb not null default '[]'::jsonb,
  ai_status             text not null default 'pending' check (ai_status in ('pending','done','failed','skipped')),
  ai_attempts           int  not null default 0,
  ai_model              text,
  ai_result             jsonb,

  created_at            timestamptz not null default now(),
  constraint uq_photo_hash_per_incident unique (incident_id, sha256)
);
create index if not exists idx_photos_incident on public.photos (incident_id, uploaded_at);
create index if not exists idx_photos_user_hash on public.photos (user_id, sha256);   -- cross-incident reuse check

-- ============ intimation_records ============
create table if not exists public.intimation_records (
  id               uuid primary key default gen_random_uuid(),
  incident_id      uuid not null references public.incidents(id) on delete cascade,
  user_id          uuid not null references auth.users(id) on delete cascade,
  channel          text not null check (channel in
    ('crop_insurance_app','helpline_14447','insurer','bank','agri_department','csc','other')),
  intimated_at     timestamptz not null,                   -- when the farmer says they did it
  reference_number text check (char_length(reference_number) <= 60),  -- ticket/ack number
  notes            text check (char_length(notes) <= 500),
  recorded_at      timestamptz not null default now(),     -- server time of this record
  created_at       timestamptz not null default now()
);
create index if not exists idx_intimations_incident on public.intimation_records (incident_id, intimated_at);

-- ============ weather_snapshots ============
create table if not exists public.weather_snapshots (
  id            uuid primary key default gen_random_uuid(),
  incident_id   uuid not null references public.incidents(id) on delete cascade,
  source        text not null default 'open-meteo',
  endpoint      text not null check (endpoint in ('forecast','archive')),
  query_lat     numeric(6,2) not null,                     -- rounded to 2 dp (privacy + cache)
  query_lng     numeric(6,2) not null,
  window_start  timestamptz not null,
  window_end    timestamptz not null,
  summary       jsonb not null,
  raw           jsonb not null,                            -- hourly arrays as returned
  fetched_at    timestamptz not null default now()
);
create index if not exists idx_weather_incident on public.weather_snapshots (incident_id, fetched_at desc);

-- ============ reports ============
create table if not exists public.reports (
  id            uuid primary key default gen_random_uuid(),
  incident_id   uuid not null references public.incidents(id) on delete cascade,
  user_id       uuid not null references auth.users(id) on delete cascade,
  version       int  not null check (version >= 1),
  storage_path  text not null,
  sha256        char(64) not null,
  size_bytes    int  not null,
  completeness  text not null check (completeness in ('complete','incomplete')),
  photo_count   int  not null,
  manifest_hash char(64) not null,
  generated_from jsonb not null,                           -- photo ids+hashes, checklist result
  generated_at  timestamptz not null default now(),
  unique (incident_id, version)
);

-- ============ audit_events (append-only chain of custody) ============
create table if not exists public.audit_events (
  id          bigint generated always as identity primary key,
  incident_id uuid references public.incidents(id) on delete cascade,
  user_id     uuid not null,
  event_type  text not null check (event_type in
    ('incident_created','incident_updated','photo_uploaded','photo_deleted',
     'intimation_recorded','intimation_deleted','weather_fetched',
     'report_generated','report_downloaded')),
  payload     jsonb not null default '{}'::jsonb,           -- never contains tokens/signed URLs
  created_at  timestamptz not null default now()
);
create index if not exists idx_audit_incident on public.audit_events (incident_id, created_at);

-- ============ Row Level Security (defence in depth; clients get SELECT on own rows only) ============
alter table public.profiles           enable row level security;
alter table public.incidents          enable row level security;
alter table public.photos             enable row level security;
alter table public.intimation_records enable row level security;
alter table public.weather_snapshots  enable row level security;
alter table public.reports            enable row level security;
alter table public.audit_events       enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='profiles' and policyname='profiles_select_own') then
    create policy profiles_select_own on public.profiles for select to authenticated using (id = (select auth.uid()));
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='incidents' and policyname='incidents_select_own') then
    create policy incidents_select_own on public.incidents for select to authenticated using (user_id = (select auth.uid()));
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='photos' and policyname='photos_select_own') then
    create policy photos_select_own on public.photos for select to authenticated using (user_id = (select auth.uid()));
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='intimation_records' and policyname='intim_select_own') then
    create policy intim_select_own on public.intimation_records for select to authenticated using (user_id = (select auth.uid()));
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='reports' and policyname='reports_select_own') then
    create policy reports_select_own on public.reports for select to authenticated using (user_id = (select auth.uid()));
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='weather_snapshots' and policyname='weather_select_own') then
    create policy weather_select_own on public.weather_snapshots for select to authenticated using (
      exists (select 1 from public.incidents i where i.id = incident_id and i.user_id = (select auth.uid())));
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='audit_events' and policyname='audit_select_own') then
    create policy audit_select_own on public.audit_events for select to authenticated using (user_id = (select auth.uid()));
  end if;
end $$;
-- No INSERT/UPDATE/DELETE policies => denied for anon/authenticated. Only the service role (FastAPI) writes.

-- ============ Storage: private bucket ============
update storage.buckets
set public = false,
    file_size_limit = 12582912,
    allowed_mime_types = array['image/jpeg','image/png','image/webp','application/pdf']
where id = 'evidence';

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('evidence','evidence', false, 12582912,
        array['image/jpeg','image/png','image/webp','application/pdf'])
on conflict (id) do nothing;
-- No storage.objects policies for clients => no direct access. Backend issues short-lived signed URLs.
