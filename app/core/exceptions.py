"""Domain exception hierarchy and centralized FastAPI exception handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AevoraException(Exception):
    """Base exception for all domain-specific Aevora AI exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "AEVORA_INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(AevoraException):
    """Raised when application configuration is missing or invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ServiceUnavailableError(AevoraException):
    """Raised when an internal or external dependency is unavailable."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized, secure exception handlers on the FastAPI application."""

    @app.exception_handler(AevoraException)
    async def aevora_exception_handler(request: Request, exc: AevoraException) -> JSONResponse:
        logger.error(
            "Domain exception encountered: code=%s message=%s path=%s",
            exc.code,
            exc.message,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled server exception during request processing: path=%s",
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please contact support.",
                }
            },
        )
