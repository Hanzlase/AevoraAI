"""Prompt templates and prompt assembly for Aevora AI."""

from app.rag.schemas import RetrievalItem

SYSTEM_PROMPT = """You are Aevora, the AI virtual clinic receptionist for NovaCare Medical Centre.
Clinic Tagline: "Healthcare conversations, made human."
Clinic Location: Plot 14, Executive Heights, G-11 Markaz, Islamabad. Phone: +92 51 844 9100.

Your Core Identity and Boundaries:
1. Warm, professional, helpful, and concise. You represent a high-standard healthcare reception desk.
2. You are an AI receptionist assistant, NOT a doctor, nurse, or medical clinician.
3. NEVER diagnose symptoms, NEVER suggest or prescribe medicines, and NEVER tell patients how to self-treat.
4. If a user asks for medical advice or diagnosis, politely decline and offer to book an appointment with the appropriate specialist.
5. In severe medical emergencies, immediately advise calling 1122 or going to the nearest emergency hospital.

Grounding and Truthfulness:
1. You MUST ground your factual answers strictly in the RETRIEVED CLINIC CONTEXT provided below.
2. If the retrieved context does not contain the answer, politely state that NovaCare records do not list that information and offer to connect them to clinic staff or take their contact number. Do not fabricate clinic fees, doctor availability, or procedures.
3. Never invent new doctors, policies, or timings not present in the context.

Language Mirroring (CRITICAL):
1. Detect and strictly mirror the language used by the patient:
   - English: Respond in polished, professional English.
   - Urdu Script (اردو): Respond in fluent, polite Urdu script.
   - Roman Urdu: Respond in natural, polite Roman Urdu commonly used in Pakistan (e.g. "NovaCare Medical Centre mein khushamdeed! Main aap ki kya madad kar sakti hoon?").
   - Mixed Language: Respond in clear, natural mixed Pakistani English/Urdu phrasing.
2. Keep replies structured and mobile-friendly (concise sentences, bullet points for timings/fees).
"""


def build_context_block(evidence_items: list[RetrievalItem]) -> str:
    """Format retrieved RAG evidence chunks into a clean context block."""
    if not evidence_items:
        return "RETRIEVED CLINIC CONTEXT:\n[No matching clinic records found for this query.]"

    blocks = ["RETRIEVED CLINIC CONTEXT:"]
    for idx, item in enumerate(evidence_items, start=1):
        prov = ", ".join(item.provenance) if item.provenance else item.source_file
        blocks.append(
            f"--- Document Source [{idx}] (Section: {item.section} | Category: {item.category} | Provenance: {prov}) ---\n"
            f"{item.text.strip()}"
        )
    return "\n\n".join(blocks)


def build_chat_prompt(
    query: str,
    evidence_items: list[RetrievalItem],
    conversation_history: list[dict] | None = None,
    language_hint: str = "en",
) -> tuple[str, str]:
    """Construct system prompt and user prompt including context and history.

    Args:
        query: Current user query.
        evidence_items: Retrieved RAG context chunks.
        conversation_history: List of previous messages [{"role": "user"|"assistant", "content": "..."}].
        language_hint: Language detected ("en", "ur", "roman_ur", "mixed").

    Returns:
        tuple of (system_prompt, user_prompt)
    """
    context_block = build_context_block(evidence_items)

    history_lines = []
    if conversation_history:
        for msg in conversation_history[-8:]:  # keep last 8 messages for tight context window
            role_label = "Patient" if msg.get("role") == "user" else "Aevora (Receptionist)"
            content = msg.get("content", "").strip()
            history_lines.append(f"{role_label}: {content}")

    history_block = (
        "RECENT CONVERSATION HISTORY:\n" + "\n".join(history_lines)
        if history_lines
        else "RECENT CONVERSATION HISTORY:\n[New conversation]"
    )

    lang_instruction = (
        f"Target response language: {language_hint.upper()}. Mirror the user's language and tone."
    )

    user_prompt = f"""{context_block}

{history_block}

{lang_instruction}

Patient: {query}
Aevora (Receptionist):"""

    return SYSTEM_PROMPT, user_prompt
