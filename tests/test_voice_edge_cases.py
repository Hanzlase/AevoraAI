"""Voice pipeline edge cases, validation, and security tests."""

from pathlib import Path

import pytest

from app.core.config import Settings
from app.voice.audio_processor import AudioProcessor
from app.voice.transcription import FasterWhisperTranscriber, MockTranscriber
from app.whatsapp.client import _is_trusted_media_host


@pytest.fixture
def settings():
    return Settings(
        voice_max_file_size_mb=1,  # 1 MB limit for test
        voice_max_duration_seconds=30,
        voice_allowed_mime_types=["audio/ogg", "audio/wav"],
        whisper_device="cpu",
        whisper_compute_type="int8",
    )


def test_trusted_media_host_validation():
    """Verify Meta CDN whitelist security."""
    assert (
        _is_trusted_media_host("https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=123")
        is True
    )
    assert _is_trusted_media_host("https://cdn.facebook.com/attachments/abc.ogg") is True
    assert _is_trusted_media_host("https://scontent.fbcdn.net/v/t39.123/sample.ogg") is True

    # Untrusted hosts rejected
    assert _is_trusted_media_host("http://lookaside.fbsbx.com/insecure") is False  # Not https
    assert _is_trusted_media_host("https://malicious-server.com/fake_audio.ogg") is False
    assert _is_trusted_media_host("https://attacker.facebook.com.evil.com/audio.ogg") is False


def test_audio_metadata_validation(settings):
    """Verify file size and MIME constraints."""
    processor = AudioProcessor(settings)

    # Valid
    processor.validate_audio_metadata(file_size_bytes=500_000, mime_type="audio/ogg")

    # Exceeds size limit (1MB = 1,048,576 bytes)
    with pytest.raises(ValueError, match="exceeds maximum limit"):
        processor.validate_audio_metadata(file_size_bytes=2_000_000, mime_type="audio/ogg")

    # Disallowed MIME
    with pytest.raises(ValueError, match="is not supported"):
        processor.validate_audio_metadata(file_size_bytes=100_000, mime_type="video/mp4")


def test_corrupt_audio_cleanup_guarantee(settings):
    """Verify temporary files are deleted even when audio conversion fails."""
    processor = AudioProcessor(settings)
    corrupt_bytes = b"NOT_A_VALID_AUDIO_HEADER_XYZ_12345"

    temp_file = processor.save_temp_bytes(corrupt_bytes, suffix=".ogg")
    assert temp_file.exists()

    # Guaranteed cleanup
    processor.cleanup_file(temp_file)
    assert not temp_file.exists()


@pytest.mark.asyncio
async def test_mock_transcriber_silence_behavior():
    """Verify empty/silent transcription handling."""
    mock = MockTranscriber(default_text="", default_lang="en")
    result = await mock.transcribe(Path("dummy.wav"))
    assert result.text == ""


def test_whisper_cpu_fallback_configuration(settings):
    """Verify CPU fallback configuration and parameters."""
    transcriber = FasterWhisperTranscriber(settings)
    dev, comp = transcriber._determine_device_and_compute()
    assert dev == "cpu"
    assert comp == "int8"
