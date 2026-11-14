"""Central conversation orchestration service."""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.gemini_client import get_llm_client
from app.ai.prompts import build_chat_prompt
from app.ai.safety import evaluate_safety
from app.core.config import get_settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.rag.service import get_rag_service
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    MessageItem,
    SourceCitation,
)
from app.services.appointment_service import AppointmentService
from app.services.handoff_service import HandoffService
from app.services.intent import classify_intent

logger = logging.getLogger("aevora.services.conversation")


class ConversationService:
    """Orchestrates conversations, memory, RAG retrieval, and AI receptionist responses."""

    @staticmethod
    def get_or_create_conversation(
        db: Session,
        conversation_id: str | None = None,
        channel: str = "web",
        external_user_id: str = "anonymous",
    ) -> Conversation:
        """Fetch an existing conversation or create a new session."""
        if conversation_id:
            conv = db.get(Conversation, conversation_id)
            if conv:
                return conv

        conv = Conversation(
            channel=channel,
            external_user_id=external_user_id,
            status="active",
            preferred_language="en",
        )
        db.add(conv)
        db.flush()
        logger.info(f"Created new conversation session: {conv.id} (channel={channel})")
        return conv

    @classmethod
    async def process_chat(cls, db: Session, request: ChatRequest) -> ChatResponse:
        """Process incoming chat turn, applying safety, workflows, RAG, and LLM generation."""
        settings = get_settings()
        conv = cls.get_or_create_conversation(
            db=db,
            conversation_id=request.conversation_id,
            channel=request.channel,
            external_user_id=request.external_user_id,
        )

        user_text = request.message.strip()
        intent_info = classify_intent(user_text)
        language = intent_info.language
        conv.preferred_language = language
        conv.last_message_at = datetime.now(UTC)

        # 1. Persist user message
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=user_text,
            intent=intent_info.intent,
            language=language,
        )
        db.add(user_msg)
        db.flush()

        # 2. Safety Evaluation (Medical emergency or clinical prescription/diagnosis deflection)
        safety = evaluate_safety(user_text, language=language)
        if not safety.is_safe:
            handoff_id = None
            if safety.requires_handoff:
                handoff = HandoffService.create_handoff(
                    db=db,
                    conversation_id=conv.id,
                    reason=safety.violation_type or "emergency_redirection",
                    summary=f"Safety deflection triggered: '{user_text}'",
                )
                handoff_id = handoff.id

            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=safety.response_message or "",
                intent=safety.violation_type,
                language=language,
            )
            db.add(asst_msg)
            db.flush()

            return ChatResponse(
                conversation_id=conv.id,
                response=safety.response_message or "",
                language=language,
                intent=safety.violation_type or "safety_deflection",
                handoff_id=handoff_id,
            )

        # 3. Handle Active In-Flight Workflows
        if conv.active_workflow == "appointment_intake":
            turn_res = AppointmentService.handle_turn(
                db=db,
                conversation=conv,
                user_message=user_text,
                language=language,
            )
            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=turn_res.response_text,
                intent="appointment_intake",
                language=language,
            )
            db.add(asst_msg)
            db.flush()

            return ChatResponse(
                conversation_id=conv.id,
                response=turn_res.response_text,
                language=language,
                intent="appointment_intake",
                workflow="appointment_intake",
                workflow_status=turn_res.status,
                appointment_id=turn_res.appointment_id,
            )

        # 4. Handle Direct Workflows (Appointment booking, cancel, human handoff)
        if intent_info.intent == "appointment_booking":
            turn_res = AppointmentService.start_workflow(
                db=db,
                conversation=conv,
                initial_message=user_text,
                language=language,
            )
            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=turn_res.response_text,
                intent="appointment_intake",
                language=language,
            )
            db.add(asst_msg)
            db.flush()

            return ChatResponse(
                conversation_id=conv.id,
                response=turn_res.response_text,
                language=language,
                intent="appointment_booking",
                workflow="appointment_intake",
                workflow_status=turn_res.status,
                appointment_id=turn_res.appointment_id,
            )

        if intent_info.intent == "appointment_cancel":
            cancelled = AppointmentService.cancel_appointment(db=db, conversation_id=conv.id)
            if cancelled:
                cancel_text = {
                    "ur": f"آپ کی اپائنٹمنٹ درخواست (ریفرنس: #{cancelled.id[:8].upper()}) منسوخ کر دی گئی ہے۔",
                    "roman_ur": f"Aap ki appointment request (Ref: #{cancelled.id[:8].upper()}) cancel kar di gayi hai.",
                    "en": f"Your pending appointment request (Ref: #{cancelled.id[:8].upper()}) has been cancelled.",
                }.get(
                    language,
                    f"Your appointment request #{cancelled.id[:8].upper()} has been cancelled.",
                )
            else:
                cancel_text = {
                    "ur": "اس چیٹ سیشن میں کوئی فعال یا پینڈنگ اپائنٹمنٹ موجود نہیں ہے۔",
                    "roman_ur": "Is conversation mein koi pending appointment request nahi mili.",
                    "en": "No pending appointment requests were found for this conversation session.",
                }.get(
                    language,
                    "No pending appointment requests were found for this conversation session.",
                )

            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=cancel_text,
                intent="appointment_cancel",
                language=language,
            )
            db.add(asst_msg)
            db.flush()

            return ChatResponse(
                conversation_id=conv.id,
                response=cancel_text,
                language=language,
                intent="appointment_cancel",
            )

        if intent_info.intent == "handoff_request":
            handoff = HandoffService.create_handoff(
                db=db,
                conversation_id=conv.id,
                reason="user_requested",
                summary=f"Patient requested human staff: '{user_text}'",
            )
            conv.status = "handed_off"
            db.flush()

            handoff_text = {
                "ur": (
                    "میں نے آپ کی درخواست نووا کیئر کے ریسیپشن عملے کو بھیج دی ہے۔ "
                    "عملے کا ایک رکن جلد از جلد آپ سے رابطہ کرے گا۔"
                ),
                "roman_ur": (
                    "Main ne aap ki request NovaCare ke clinic staff ko forward kar di hai. "
                    "Hamaari team ka member jald aap se rabta karega."
                ),
                "en": (
                    "I have connected your request with our human reception desk at NovaCare Medical Centre. "
                    "A staff member will follow up with you shortly."
                ),
            }.get(language, "A staff member will follow up with you shortly.")

            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=handoff_text,
                intent="handoff_request",
                language=language,
            )
            db.add(asst_msg)
            db.flush()

            return ChatResponse(
                conversation_id=conv.id,
                response=handoff_text,
                language=language,
                intent="handoff_request",
                handoff_id=handoff.id,
            )

        # 5. Grounded RAG Retrieval and LLM Generation
        rag_service = get_rag_service()
        retrieval = rag_service.retrieve(
            query=user_text,
            top_k=settings.ai_max_context_chunks,
        )

        source_citations = [
            SourceCitation(
                entity_id=item.entity_id or item.chunk_id,
                category=item.category,
                section=item.section,
                provenance=", ".join(item.provenance) if item.provenance else item.source_file,
            )
            for item in retrieval.evidence
        ]

        # Gather recent conversation history for context
        history_msgs = [
            {"role": m.role, "content": m.content}
            for m in conv.messages[-settings.ai_max_history_messages :]
        ]

        sys_prompt, user_prompt = build_chat_prompt(
            query=user_text,
            evidence_items=retrieval.evidence,
            conversation_history=history_msgs,
            language_hint=language,
        )

        llm_client = get_llm_client()
        try:
            response_text = await llm_client.generate(
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_output_tokens,
            )
        except Exception as err:
            logger.error(f"Error generating LLM response: {err}. Using grounded fallback.")
            if retrieval.evidence:
                top_text = retrieval.evidence[0].text.strip()
                if language == "ur":
                    response_text = f"نووا کیئر کلینک کے ریکارڈ کے مطابق:\n\n{top_text}"
                elif language in ("roman_ur", "mixed"):
                    response_text = f"NovaCare records ke mutabiq:\n\n{top_text}"
                else:
                    response_text = f"According to NovaCare Medical Centre records:\n\n{top_text}"
            else:
                if language == "ur":
                    response_text = "معذرت، نووا کیئر کے ریکارڈ میں یہ معلومات دستیاب نہیں ہیں۔ مزید معلومات کے لیے براہ کرم ہمارے کلینک نمبر +92 51 844 9100 پر رابطہ کریں۔"
                elif language in ("roman_ur", "mixed"):
                    response_text = "Maazrat, NovaCare ke records mein yeh details mojood nahi hain. Barah-e-karam clinic reception number +92 51 844 9100 par rabta karein."
                else:
                    response_text = "I apologize, but this information is not found in NovaCare's records. Please contact clinic reception directly at +92 51 844 9100."

        # Persist assistant response
        asst_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=response_text,
            intent=intent_info.intent,
            language=language,
            sources=[s.model_dump() for s in source_citations],
        )
        db.add(asst_msg)
        db.flush()

        return ChatResponse(
            conversation_id=conv.id,
            response=response_text,
            language=language,
            intent=intent_info.intent,
            sources=source_citations,
        )

    @staticmethod
    def get_conversation_history(
        db: Session, conversation_id: str
    ) -> ConversationHistoryResponse | None:
        """Fetch full conversation history."""
        conv = db.get(Conversation, conversation_id)
        if not conv:
            return None

        message_items = [
            MessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                language=m.language,
                sources=m.sources if isinstance(m.sources, list) else None,
                created_at=m.created_at,
            )
            for m in conv.messages
        ]

        return ConversationHistoryResponse(
            conversation_id=conv.id,
            channel=conv.channel,
            external_user_id=conv.external_user_id,
            status=conv.status,
            preferred_language=conv.preferred_language,
            created_at=conv.created_at,
            last_message_at=conv.last_message_at,
            messages=message_items,
        )

    @staticmethod
    def delete_conversation(db: Session, conversation_id: str) -> bool:
        """Delete conversation and related messages (cascade)."""
        conv = db.get(Conversation, conversation_id)
        if not conv:
            return False
        db.delete(conv)
        db.flush()
        logger.info(f"Deleted conversation: {conversation_id}")
        return True
