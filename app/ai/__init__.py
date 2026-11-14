"""AI package exports."""

from app.ai.gemini_client import (
    BaseLLMClient,
    GeminiClient,
    MockLLMClient,
    get_llm_client,
    set_llm_client,
)
from app.ai.prompts import SYSTEM_PROMPT, build_chat_prompt, build_context_block
from app.ai.safety import SafetyCheckResult, evaluate_safety

__all__ = [
    "SYSTEM_PROMPT",
    "BaseLLMClient",
    "GeminiClient",
    "MockLLMClient",
    "SafetyCheckResult",
    "build_chat_prompt",
    "build_context_block",
    "evaluate_safety",
    "get_llm_client",
    "set_llm_client",
]
