"""Supabase client singleton using service-role key."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    """Return a cached Supabase client using the service-role key.

    The service role bypasses RLS (app-level ownership checks are the primary control).
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
