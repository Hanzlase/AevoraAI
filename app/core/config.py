"""Application configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings with typed schema and secret masking."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application Metadata
    app_name: str = Field(default="Aevora AI", description="Public name of the application")
    environment: str = Field(
        default="development",
        description="Deployment environment (development, staging, production)",
    )
    version: str = Field(default="0.1.0", description="Application semantic version")
    debug: bool = Field(default=False, description="Debug mode flag")
    api_prefix: str = Field(default="/api/v1", description="Prefix for versioned API routes")
    log_level: str = Field(default="INFO", description="Global logging level")

    # Database (Phase 03 preparation)
    database_url: str = Field(
        default="sqlite:///./aevora.db",
        description="Database connection URL",
    )

    # Google Gemini API (Phase 03 preparation - optional in Phase 01)
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description="Google AI Studio Gemini API key",
    )
    gemini_model: str = Field(
        default="gemini-3.8-flash",
        description="Configurable Gemini model identifier",
    )

    # Meta / WhatsApp Cloud API (Phase 04 preparation - optional in Phase 01)
    whatsapp_access_token: SecretStr | None = Field(
        default=None,
        description="Meta WhatsApp Cloud API system user or temporary access token",
    )
    whatsapp_phone_number_id: str | None = Field(
        default=None,
        description="Meta WhatsApp sender phone number ID",
    )
    whatsapp_waba_id: str | None = Field(
        default=None,
        description="Meta WhatsApp Business Account ID",
    )
    meta_app_id: str | None = Field(
        default=None,
        description="Meta developer application ID",
    )
    meta_app_secret: SecretStr | None = Field(
        default=None,
        description="Meta developer application secret for webhook signature verification",
    )
    webhook_verify_token: SecretStr | None = Field(
        default=None,
        description="Custom secret token for Meta webhook subscription verification",
    )

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Provide a cached instance of the loaded application settings."""
    return Settings()
