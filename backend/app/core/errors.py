"""Structured error responses and exception classes per SPEC section 7."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------
class AppError(Exception):
    """Base application error with structured response support."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        details: list[dict[str, Any]] | None = None,
    ):
        self.message = message
        self.details = details or []
        super().__init__(message)


class UnauthenticatedError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"

    def __init__(self, message: str = "Missing, invalid, or expired token."):
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found."):
        super().__init__(message)


class DuplicatePhotoError(AppError):
    status_code = 409
    code = "PHOTO_DUPLICATE"

    def __init__(
        self,
        message: str = "This photo has already been uploaded to this incident.",
        details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message, details)


class PhotoLimitError(AppError):
    status_code = 409
    code = "PHOTO_LIMIT_REACHED"

    def __init__(self, message: str = "Maximum number of photos reached for this incident."):
        super().__init__(message)


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"

    def __init__(
        self, message: str = "Validation failed.", details: list[dict[str, Any]] | None = None
    ):
        super().__init__(message, details)


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"

    def __init__(self, message: str = "File exceeds the maximum allowed size."):
        super().__init__(message)


class UnsupportedMediaError(AppError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"

    def __init__(self, message: str = "File type is not supported."):
        super().__init__(message)


class RateLimitedError(AppError):
    status_code = 429
    code = "RATE_LIMITED"

    def __init__(self, message: str = "Too many requests. Please try again later."):
        super().__init__(message)


class UpstreamUnavailableError(AppError):
    status_code = 502
    code = "UPSTREAM_UNAVAILABLE"

    def __init__(self, message: str = "An upstream service is temporarily unavailable."):
        super().__init__(message)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _error_body(code: str, message: str, details: list, request_id: str) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details, _get_request_id(request)),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        details.append({"field": field, "issue": err.get("msg", "")})
    return JSONResponse(
        status_code=422,
        content=_error_body(
            "VALIDATION_ERROR", "Validation failed.", details, _get_request_id(request)
        ),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_error_body(
            "INTERNAL_ERROR", "An unexpected error occurred.", [], _get_request_id(request)
        ),
    )
