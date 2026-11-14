"""FastAPI application factory and main entry point for Aevora AI."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import HealthResponse
from app.api.routes.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle events."""
    settings = get_settings()
    logger.info(
        "Starting %s (v%s) in [%s] environment",
        settings.app_name,
        settings.version,
        settings.environment,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure an instance of the FastAPI application.

    Args:
        settings: Optional custom settings instance (useful for testing overrides).

    Returns:
        Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_settings()

    setup_logging(settings.log_level)

    app = FastAPI(
        title="Aevora AI — Clinic Receptionist Assistant API",
        description=(
            "Multilingual WhatsApp clinic receptionist backend for NovaCare Medical Centre. "
            "Handles administrative inquiries, clinic directory, appointment requests, "
            "and triage escalation."
        ),
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # Register centralized domain exception handlers
    register_exception_handlers(app)

    # Dependency override for settings when explicitly provided
    from app.api.dependencies import get_current_settings

    app.dependency_overrides[get_current_settings] = lambda: settings

    # Basic CORS middleware configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production() else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Versioned API routes (e.g., /api/v1/health)
    app.include_router(health_router, prefix=settings.api_prefix)

    # Root /health alias for container health checks and local convenience
    @app.get(
        "/health",
        response_model=HealthResponse,
        include_in_schema=False,
        summary="Root Health Alias",
    )
    async def root_health(
        settings_dep: Settings = Depends(get_current_settings),
    ) -> HealthResponse:
        return HealthResponse(
            status="healthy",
            service=settings_dep.app_name,
            version=settings_dep.version,
            environment=settings_dep.environment,
        )

    return app


# Default application instance for Uvicorn
app = create_app()
