"""Multilingual audio transcription service using Faster-Whisper with CPU/GPU auto-detection."""

import abc
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger("aevora.voice.transcription")


@dataclass
class TranscriptionResult:
    """Outcome of audio transcription."""

    text: str
    language: str
    confidence: float
    duration_seconds: float


class BaseTranscriber(abc.ABC):
    """Abstract interface for speech-to-text transcribers."""

    @abc.abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Transcribe an audio file into text."""
        pass


class FasterWhisperTranscriber(BaseTranscriber):
    """Production transcriber utilizing Faster-Whisper and CTranslate2."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = None
        self._device: str | None = None
        self._compute_type: str | None = None
        self._semaphore = asyncio.Semaphore(self.settings.voice_max_concurrent_jobs)

    def _determine_device_and_compute(self) -> tuple[str, str]:
        """Detect execution device and precision with safe CPU fallback."""
        target_device = self.settings.whisper_device.lower()
        target_compute = self.settings.whisper_compute_type.lower()

        if target_device == "cpu":
            compute = "int8" if target_compute == "auto" else target_compute
            return "cpu", compute

        # Auto or CUDA requested
        try:
            import ctranslate2

            cuda_count = ctranslate2.get_cuda_device_count()
            if cuda_count > 0:
                logger.info(f"Detected {cuda_count} CUDA GPU(s). Using CUDA device for Whisper.")
                compute = "float16" if target_compute == "auto" else target_compute
                return "cuda", compute
        except Exception as exc:
            logger.warning(f"CUDA detection failed or unavailable: {exc}. Falling back to CPU.")

        compute = "int8" if target_compute == "auto" else target_compute
        return "cpu", compute

    def _load_model(self) -> Any:
        """Lazily load Faster-Whisper model on first transcription request."""
        if self._model is not None:
            return self._model

        from faster_whisper import WhisperModel

        device, compute_type = self._determine_device_and_compute()
        self._device = device
        self._compute_type = compute_type

        logger.info(
            f"Loading Faster-Whisper model '{self.settings.whisper_model_size}' "
            f"on [{device.upper()}] with compute [{compute_type}]..."
        )

        try:
            self._model = WhisperModel(
                self.settings.whisper_model_size,
                device=device,
                compute_type=compute_type,
                download_root=self.settings.whisper_download_root,
                cpu_threads=self.settings.whisper_cpu_threads,
                num_workers=self.settings.whisper_num_workers,
            )
            logger.info("Faster-Whisper model loaded successfully.")
        except Exception as exc:
            if device != "cpu":
                logger.warning(
                    f"Failed to initialize Whisper on {device}: {exc}. Retrying on CPU..."
                )
                self._device = "cpu"
                self._compute_type = "int8"
                self._model = WhisperModel(
                    self.settings.whisper_model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=self.settings.whisper_download_root,
                    cpu_threads=self.settings.whisper_cpu_threads,
                )
                logger.info("Faster-Whisper model loaded successfully on CPU fallback.")
            else:
                raise

        return self._model

    def _sync_transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Run blocking Whisper model inference in thread pool."""
        model = self._load_model()
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            task="transcribe",
            vad_filter=True,  # Voice activity detection to trim silence
        )

        text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        full_text = " ".join(text_parts).strip()

        return TranscriptionResult(
            text=full_text,
            language=info.language or "en",
            confidence=float(info.language_probability or 0.0),
            duration_seconds=float(info.duration or 0.0),
        )

    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Asynchronously transcribe audio using bounded concurrency and thread offloading."""
        async with self._semaphore:
            return await asyncio.to_thread(self._sync_transcribe, audio_path)


class MockTranscriber(BaseTranscriber):
    """Deterministic mock transcriber for unit and integration testing."""

    def __init__(
        self,
        default_text: str = "Dr Farhan ki consultation fee kitni hai?",
        default_lang: str = "roman_ur",
    ) -> None:
        self.default_text = default_text
        self.default_lang = default_lang
        self.call_history: list[Path] = []

    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        self.call_history.append(audio_path)
        return TranscriptionResult(
            text=self.default_text,
            language=self.default_lang,
            confidence=0.98,
            duration_seconds=3.5,
        )


_transcriber_instance: BaseTranscriber | None = None


def get_transcriber() -> BaseTranscriber:
    """Get active transcriber singleton."""
    global _transcriber_instance
    if _transcriber_instance is None:
        _transcriber_instance = FasterWhisperTranscriber()
    return _transcriber_instance


def set_transcriber(transcriber: BaseTranscriber | None) -> None:
    """Override active transcriber (for testing)."""
    global _transcriber_instance
    _transcriber_instance = transcriber
