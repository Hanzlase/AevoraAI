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

    # Google Gemini API & Receptionist Settings (Phase 03)
    gemini_api_key: SecretStr | None = Field(
        default=None,
        description="Google AI Studio Gemini API key",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Configurable Gemini model identifier",
    )
    ai_timeout_seconds: int = Field(
        default=30,
        description="Timeout in seconds for external LLM API calls",
    )
    ai_max_history_messages: int = Field(
        default=12,
        description="Maximum number of historical conversation messages to supply as context",
    )
    ai_max_context_chunks: int = Field(
        default=5,
        description="Maximum number of RAG chunks to supply as context to the generator",
    )
    ai_max_output_tokens: int = Field(
        default=1000,
        description="Maximum tokens generated per LLM response",
    )
    ai_temperature: float = Field(
        default=0.2,
        description="Sampling temperature for LLM response generation",
    )

    # Meta / WhatsApp Cloud API (Phase 04)
    whatsapp_enabled: bool = Field(
        default=False,
        description="Master flag to enable Meta WhatsApp Cloud API integration",
    )
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
    whatsapp_graph_api_version: str = Field(
        default="v22.0",
        description="Configurable Meta Graph API version",
    )
    whatsapp_api_timeout_seconds: int = Field(
        default=20,
        description="HTTP timeout for outbound Graph API calls",
    )
    whatsapp_max_retries: int = Field(
        default=2,
        description="Maximum retry attempts for transient Graph API failures",
    )
    whatsapp_webhook_max_body_bytes: int = Field(
        default=1048576,
        description="Maximum allowed raw webhook payload size in bytes (1MB default)",
    )
    whatsapp_event_worker_enabled: bool = Field(
        default=True,
        description="Run internal background event consumer for durable inbound webhook queue",
    )
    whatsapp_event_poll_interval_seconds: float = Field(
        default=1.0,
        description="Poll interval in seconds for durable webhook event worker",
    )
    whatsapp_max_event_attempts: int = Field(
        default=5,
        description="Maximum attempts to process a single inbound webhook event",
    )

    # Voice / Audio & Faster-Whisper Settings (Phase 04)
    voice_input_enabled: bool = Field(
        default=True,
        description="Enable incoming voice note audio processing",
    )
    voice_max_file_size_mb: int = Field(
        default=16,
        description="Maximum allowed audio file size in megabytes (Meta default is 16MB)",
    )
    voice_max_duration_seconds: int = Field(
        default=180,
        description="Maximum allowed voice note duration in seconds",
    )
    voice_temp_dir: str = Field(
        default="temp_audio",
        description="Temporary directory path for voice note conversion and transcription",
    )
    voice_allowed_mime_types: list[str] = Field(
        default=[
            "audio/ogg",
            "audio/ogg; codecs=opus",
            "audio/mpeg",
            "audio/mp4",
            "audio/aac",
            "audio/amr",
            "audio/wav",
            "audio/webm",
        ],
        description="Permitted audio MIME types for incoming voice notes",
    )
    ffmpeg_binary: str = Field(
        default="ffmpeg",
        description="Path or binary name for FFmpeg (defaults to 'ffmpeg', falls back to imageio-ffmpeg)",
    )
    voice_processing_timeout_seconds: int = Field(
        default=120,
        description="Overall timeout for audio download, conversion, and transcription",
    )
    voice_max_concurrent_jobs: int = Field(
        default=1,
        description="Maximum concurrent transcription jobs on workstation",
    )
    whisper_model_size: str = Field(
        default="base",
        description="Faster-Whisper model size identifier (tiny, base, small, medium)",
    )
    whisper_device: str = Field(
        default="auto",
        description="Execution device: auto, cpu, or cuda",
    )
    whisper_compute_type: str = Field(
        default="auto",
        description="Compute precision: auto, int8, float16, float32",
    )
    whisper_download_root: str | None = Field(
        default=None,
        description="Custom directory to cache Faster-Whisper model weights",
    )
    whisper_cpu_threads: int = Field(
        default=4,
        description="CPU threads allocated to Faster-Whisper",
    )
    whisper_num_workers: int = Field(
        default=1,
        description="Number of workers for Faster-Whisper",
    )

    # Optional Spoken Replies / TTS (Phase 04 - disabled by default)
    voice_reply_enabled: bool = Field(
        default=False,
        description="Generate and send spoken audio voice notes alongside text replies",
    )
    voice_reply_provider: str = Field(
        default="edge_tts",
        description="TTS provider identifier",
    )
    voice_reply_language_mode: str = Field(
        default="match_user",
        description="TTS voice selection mode (match_user or fixed)",
    )
    voice_reply_timeout_seconds: int = Field(
        default=30,
        description="Timeout for generating and uploading audio reply",
    )

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Provide a cached instance of the loaded application settings."""
    return Settings()
