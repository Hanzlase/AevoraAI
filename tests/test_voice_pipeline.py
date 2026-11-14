"""Tests for audio file validation, FFmpeg resolution, Faster-Whisper device detection, and TTS."""

import pytest

from app.core.config import Settings
from app.voice.audio_processor import AudioProcessor, resolve_ffmpeg_binary
from app.voice.transcription import (
    FasterWhisperTranscriber,
    MockTranscriber,
)
from app.voice.tts import generate_speech


def test_audio_metadata_validation():
    processor = AudioProcessor()

    # Valid audio
    processor.validate_audio_metadata(
        file_size_bytes=5 * 1024 * 1024,
        mime_type="audio/ogg; codecs=opus",
    )

    # Oversized audio (> 16MB)
    with pytest.raises(ValueError, match="exceeds maximum limit"):
        processor.validate_audio_metadata(
            file_size_bytes=20 * 1024 * 1024,
            mime_type="audio/ogg",
        )

    # Disallowed MIME type
    with pytest.raises(ValueError, match="not supported"):
        processor.validate_audio_metadata(
            file_size_bytes=1024,
            mime_type="video/mp4",
        )


def test_ffmpeg_binary_resolution():
    exe = resolve_ffmpeg_binary()
    assert exe is not None
    assert len(exe) > 0


def test_whisper_device_selection_cpu():
    cfg = Settings(whisper_device="cpu", whisper_compute_type="auto")
    transcriber = FasterWhisperTranscriber(settings=cfg)
    device, compute = transcriber._determine_device_and_compute()
    assert device == "cpu"
    assert compute == "int8"


@pytest.mark.asyncio
async def test_mock_transcriber(tmp_path):
    dummy_wav = tmp_path / "test.wav"
    dummy_wav.write_bytes(b"dummy")

    transcriber = MockTranscriber(default_text="Dr Bilal fee", default_lang="en")
    res = await transcriber.transcribe(dummy_wav)
    assert res.text == "Dr Bilal fee"
    assert res.language == "en"
    assert len(transcriber.call_history) == 1


@pytest.mark.asyncio
async def test_optional_tts_disabled_by_default():
    cfg = Settings(voice_reply_enabled=False)
    result = await generate_speech("Hello", "en", settings=cfg)
    assert result is None
