"""Operational health check endpoint for monitoring and smoke testing."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_settings
from app.core.config import Settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Safe operational health status payload.

    Exposes only essential operational metadata without leaking internal secrets,
    database connection strings, or pretending that unverified AI / Meta subsystems
    are healthy.
    """

    status: str = Field(..., description="Operational status of the core API service")
    service: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Current operating environment")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns baseline operational health status and service metadata.",
)
async def get_health(settings: Settings = Depends(get_current_settings)) -> HealthResponse:
    """Safe health check endpoint.

    Reports only safe operational information (status, service name, version, and
    environment). Does not perform or report fake checks for unbuilt subsystems.
    """
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )
