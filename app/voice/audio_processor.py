"""Audio file validation, temporary file lifecycle, and FFmpeg conversion."""

import asyncio
import logging
import os
import shutil
import uuid
from pathlib import Path

import imageio_ffmpeg

from app.core.config import Settings, get_settings

logger = logging.getLogger("aevora.voice.processor")


def resolve_ffmpeg_binary(configured_binary: str | None = None) -> str:
    """Locate executable FFmpeg binary, falling back to imageio-ffmpeg bundled binary."""
    if configured_binary and shutil.which(configured_binary):
        return configured_binary

    try:
        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and os.path.exists(bundled):
            return bundled
    except Exception as exc:
        logger.warning(f"Could not resolve bundled FFmpeg binary: {exc}")

    return "ffmpeg"


class AudioProcessor:
    """Manages audio validation, temp files, and conversion to 16kHz WAV."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.temp_dir = Path(self.settings.voice_temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = resolve_ffmpeg_binary(self.settings.ffmpeg_binary)

    def validate_audio_metadata(
        self,
        file_size_bytes: int,
        mime_type: str,
    ) -> None:
        """Validate audio constraints against security and operational limits."""
        max_bytes = self.settings.voice_max_file_size_mb * 1024 * 1024
        if file_size_bytes > max_bytes:
            raise ValueError(
                f"Audio file size ({file_size_bytes} bytes) exceeds maximum limit "
                f"({self.settings.voice_max_file_size_mb} MB)."
            )

        clean_mime = mime_type.split(";")[0].strip().lower()
        allowed = [m.split(";")[0].strip().lower() for m in self.settings.voice_allowed_mime_types]
        if clean_mime not in allowed:
            raise ValueError(f"Audio MIME type '{mime_type}' is not supported. Allowed: {allowed}")

    def save_temp_bytes(self, data: bytes, suffix: str = ".ogg") -> Path:
        """Atomically write audio bytes to a randomly named temporary file."""
        filename = f"voice_{uuid.uuid4().hex}{suffix}"
        filepath = self.temp_dir / filename
        filepath.write_bytes(data)
        return filepath

    async def convert_to_wav(self, input_path: Path) -> Path:
        """Convert arbitrary audio format (OGG Opus, AAC, M4A) to 16kHz mono WAV using FFmpeg."""
        output_path = input_path.with_suffix(".wav")
        cmd = [
            self.ffmpeg_bin,
            "-y",  # Overwrite output without prompting
            "-i",
            str(input_path),
            "-ar",
            "16000",  # 16kHz sample rate required by Whisper
            "-ac",
            "1",  # Mono channel
            "-c:a",
            "pcm_s16le",  # 16-bit PCM WAV
            str(output_path),
        ]

        logger.debug(f"Converting audio via FFmpeg: {input_path.name} -> {output_path.name}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=float(self.settings.voice_processing_timeout_seconds),
            )
        except TimeoutError:
            process.kill()
            raise TimeoutError("FFmpeg audio conversion timed out.") from None

        if process.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace")
            logger.error(f"FFmpeg conversion failed: {err_msg}")
            raise RuntimeError(f"FFmpeg audio conversion failed: {err_msg}")

        return output_path

    @staticmethod
    def cleanup_file(path: Path | None) -> None:
        """Safely delete temporary audio file."""
        if path and path.exists():
            try:
                path.unlink()
                logger.debug(f"Cleaned temporary file: {path.name}")
            except Exception as exc:
                logger.warning(f"Failed to remove temp file {path}: {exc}")
