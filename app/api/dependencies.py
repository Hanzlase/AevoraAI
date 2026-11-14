"""FastAPI route dependencies for configuration and services."""

from app.core.config import Settings, get_settings


def get_current_settings() -> Settings:
    """Dependency provider for cached application settings."""
    return get_settings()
