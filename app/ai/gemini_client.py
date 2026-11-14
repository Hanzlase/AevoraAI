"""LLM client interface and Google Gemini implementation with timeout and fallback."""

import abc
import asyncio
import logging
from typing import Any

from google import genai
from google.genai import types

from app.core.config import Settings, get_settings

logger = logging.getLogger("aevora.ai.gemini")

FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-1.5-flash"]


class BaseLLMClient(abc.ABC):
    """Abstract base class for LLM providers."""

    @abc.abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> str:
        """Generate response text from LLM."""
        pass


class GeminiClient(BaseLLMClient):
    """Concrete Gemini API client using the official Google GenAI SDK."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        api_key = (
            self.settings.gemini_api_key.get_secret_value()
            if self.settings.gemini_api_key
            else None
        )
        if not api_key:
            self._client = None
            logger.warning(
                "GeminiClient initialized without GEMINI_API_KEY. Calls will fail or fallback."
            )
        else:
            self._client = genai.Client(
                api_key=api_key,
                http_options={"api_version": "v1beta"},
            )

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> str:
        """Call Gemini generate_content asynchronously with retries, timeout, and model fallback."""
        if not self._client:
            raise RuntimeError("Gemini API key is not configured in settings.")

        models_to_try = [self.settings.gemini_model]
        for fb in FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )

        last_error: Exception | None = None

        for model_name in models_to_try:
            try:
                logger.debug(f"Attempting LLM generation with model: {model_name}")
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=model_name,
                        contents=user_prompt,
                        config=config,
                    ),
                    timeout=float(self.settings.ai_timeout_seconds),
                )
                if response and response.text:
                    return response.text.strip()
                raise ValueError("Empty response received from Gemini API.")
            except TimeoutError as err:
                logger.warning(f"Timeout calling Gemini with model {model_name}: {err}")
                last_error = err
            except Exception as err:
                logger.warning(
                    f"Gemini API call failed for model {model_name}: {type(err).__name__}: {err}"
                )
                last_error = err

        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


class MockLLMClient(BaseLLMClient):
    """Deterministic mock client for offline unit and integration tests."""

    def __init__(self, default_response: str | None = None) -> None:
        self.default_response = (
            default_response
            or "Thank you for contacting NovaCare Medical Centre. How can I assist you with your appointment today?"
        )
        self.call_history: list[dict[str, Any]] = []

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 600,
    ) -> str:
        self.call_history.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.default_response


_llm_client_instance: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    """Singleton-style accessor for LLM client."""
    global _llm_client_instance
    if _llm_client_instance is None:
        settings = get_settings()
        if settings.gemini_api_key and settings.gemini_api_key.get_secret_value():
            _llm_client_instance = GeminiClient(settings)
        else:
            _llm_client_instance = MockLLMClient()
    return _llm_client_instance


def set_llm_client(client: BaseLLMClient | None) -> None:
    """Override LLM client (useful for testing)."""
    global _llm_client_instance
    _llm_client_instance = client
