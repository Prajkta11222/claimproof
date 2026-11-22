"""Health check endpoint — public, no auth."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness check. Returns status and version."""
    return {"status": "ok", "version": "0.1.0"}
