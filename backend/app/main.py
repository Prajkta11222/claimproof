"""FastAPI application factory (SPEC section 5.1)."""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.checklist import router as checklist_router

# Import routers
from app.api.v1.health import router as health_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.intimations import router as intimations_router
from app.api.v1.me import router as me_router
from app.api.v1.photos import router as photos_router
from app.api.v1.reports import router as reports_router
from app.api.v1.weather import router as weather_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    RateLimitedError,
    app_error_handler,
    generic_error_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.core.rules import (
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_UPLOAD,
    REPORT_MAX_PER_INCIDENT_PER_HOUR,
)
from app.core.security import verify_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate settings on startup (fail fast)."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger = structlog.get_logger()
    logger.info("app_starting", env=settings.app_env)
    yield
    logger.info("app_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    rate_lock = threading.Lock()
    rate_windows: dict[tuple[str, str, str], tuple[datetime, int]] = {}

    def parse_limit(value: str) -> tuple[int, timedelta]:
        count_text, period_text = value.split("/", 1)
        count = int(count_text)
        period = (
            60 if period_text.startswith("min") else (3600 if period_text.startswith("hour") else 1)
        )
        return count, timedelta(seconds=period)

    def get_user_key(request: Request) -> str | None:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        try:
            claims = verify_token(auth[7:], settings)
            return str(claims["sub"])
        except Exception:
            return None

    def enforce_rate_limit(request: Request, request_id: str) -> Response | None:
        user_key = get_user_key(request)
        if user_key is None or request.url.path == "/api/v1/health":
            return None

        path = request.url.path
        method = request.method.upper()
        if method == "POST" and "/photos" in path:
            limit_text = RATE_LIMIT_UPLOAD
            scope = "photo-upload"
        elif method == "POST" and "/reports" in path:
            limit_text = f"{REPORT_MAX_PER_INCIDENT_PER_HOUR}/hour"
            parts = path.strip("/").split("/")
            scope = f"report:{parts[3]}" if len(parts) > 3 else "report"
        else:
            limit_text = RATE_LIMIT_DEFAULT
            scope = "default"

        limit, window = parse_limit(limit_text)
        if scope in ("photo-upload", "default"):
            key = (scope, user_key, "*")
        else:
            key = (scope, user_key, scope)
        now = datetime.now(timezone.utc)
        with rate_lock:
            started_at, count = rate_windows.get(key, (now, 0))
            if now - started_at >= window:
                started_at, count = now, 0
            count += 1
            rate_windows[key] = (started_at, count)

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please try again later.",
                        "details": [],
                        "request_id": request_id,
                    }
                },
                headers={"X-Request-ID": request_id},
            )
        return None

    app = FastAPI(
        title="ClaimProof API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env == "development" else None,
        lifespan=lifespan,
    )

    # --- Rate limiter ---
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # --- Middleware: Request ID, security headers, logging ---
    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        # Request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger = structlog.get_logger()
        start_time = time.monotonic()

        limited = enforce_rate_limit(request, request_id)
        if limited is not None:
            return limited

        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception("unhandled_error", path=request.url.path)
            raise

        elapsed_ms = round((time.monotonic() - start_time) * 1000, 1)

        # Security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.headers.get("Authorization"):
            response.headers["Cache-Control"] = "no-store"

        # Log request (no PII: no tokens, no GPS, no file contents)
        logger.info(
            "request_complete",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )

        return response

    # --- Exception handlers ---
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        err = RateLimitedError()
        return await app_error_handler(request, err)

    # --- Routes ---
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(me_router, prefix="/api/v1", tags=["profile"])
    app.include_router(incidents_router, prefix="/api/v1", tags=["incidents"])
    app.include_router(intimations_router, prefix="/api/v1", tags=["intimations"])
    app.include_router(photos_router, prefix="/api/v1", tags=["photos"])
    app.include_router(checklist_router, prefix="/api/v1", tags=["checklist"])
    app.include_router(weather_router, prefix="/api/v1", tags=["weather"])
    app.include_router(reports_router, prefix="/api/v1", tags=["reports"])

    return app


app = create_app()
