"""Tests for Gemini client, prompt formatting, and error handling."""

import pytest

from app.ai.gemini_client import GeminiClient, MockLLMClient
from app.ai.prompts import build_chat_prompt, build_context_block
from app.core.config import Settings
from app.rag.schemas import RetrievalItem


def test_build_context_block_formatting():
    items = [
        RetrievalItem(
            chunk_id="chunk_1",
            text="Clinic timings: Monday to Saturday 9am to 8pm.",
            category="administrative",
            section="Timings & Hours",
            entity_id="entity_timings",
            source_type="json",
            source_file="NovaCare_RAG_Source_of_Truth.json",
            hybrid_score=0.95,
            provenance=["NovaCare_RAG_Source_of_Truth.json"],
        ),
        RetrievalItem(
            chunk_id="chunk_2",
            text="Dr. Farhan Consultation Fee is PKR 3,000.",
            category="doctor_profile",
            section="Consultant Cardiologist",
            entity_id="doc_farhan",
            source_type="pdf",
            source_file="NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf",
            hybrid_score=0.88,
            provenance=["NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf p.3"],
        ),
    ]
    block = build_context_block(items)
    assert "Timings & Hours" in block
    assert "Consultant Cardiologist" in block
    assert "PKR 3,000" in block


def test_build_chat_prompt_with_history():
    items = [
        RetrievalItem(
            chunk_id="c1",
            text="Dr. Farhan is available on Monday and Wednesday.",
            category="doctor",
            section="Cardiology",
            entity_id="doc_farhan",
            source_type="json",
            source_file="NovaCare_RAG_Source_of_Truth.json",
            hybrid_score=0.9,
            provenance=["NovaCare_RAG_Source_of_Truth.json"],
        )
    ]
    history = [
        {"role": "user", "content": "Hello Aevora"},
        {"role": "assistant", "content": "Hello! Welcome to NovaCare Medical Centre."},
    ]
    sys_prompt, user_prompt = build_chat_prompt(
        query="When can I see Dr. Farhan?",
        evidence_items=items,
        conversation_history=history,
        language_hint="en",
    )
    assert "Healthcare conversations, made human" in sys_prompt
    assert "Hello Aevora" in user_prompt
    assert "When can I see Dr. Farhan?" in user_prompt
    assert "TARGET RESPONSE LANGUAGE: EN" in user_prompt.upper()


@pytest.mark.asyncio
async def test_mock_llm_client():
    client = MockLLMClient(default_response="Mocked clinic answer")
    resp = await client.generate("system prompt", "user prompt")
    assert resp == "Mocked clinic answer"
    assert len(client.call_history) == 1
    assert client.call_history[0]["user_prompt"] == "user prompt"


@pytest.mark.asyncio
async def test_gemini_client_without_api_key_raises_runtime_error():
    dummy_settings = Settings(gemini_api_key=None)
    client = GeminiClient(settings=dummy_settings)
    with pytest.raises(RuntimeError, match="Gemini API key is not configured"):
        await client.generate("system", "user")
