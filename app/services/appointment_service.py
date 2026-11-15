"""Appointment intake workflow and state machine."""

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.appointment import AppointmentRequest
from app.models.conversation import Conversation

logger = logging.getLogger("aevora.services.appointment")

PHONE_PATTERN = re.compile(r"(\+?92\s?[0-9]{3}\s?[0-9]{7}|03[0-9]{2}\s?[0-9]{7}|03\d{9})")
CONFIRMATION_POSITIVE = re.compile(
    r"\b(yes|confirm|proceed|ok|okay|theek\s+hai|haan|ji\s+haan|bilkul|confirm\s+karein)\b",
    re.IGNORECASE,
)
CONFIRMATION_NEGATIVE = re.compile(
    r"\b(no|cancel|stop|nah|nahi|nhi|mansookh|mat\s+karein)\b",
    re.IGNORECASE,
)


@dataclass
class WorkflowTurnResult:
    """Outcome of processing an appointment workflow turn."""

    response_text: str
    workflow_active: bool
    status: str  # in_progress, awaiting_confirmation, confirmed, cancelled
    appointment_id: str | None = None


class AppointmentService:
    """State machine governing multi-turn progressive appointment intake."""

    @staticmethod
    def _extract_slots_from_text(text: str, current_fields: dict) -> dict:
        """Heuristic slot extraction from user input."""
        updated = dict(current_fields)

        # Phone extraction
        phone_match = PHONE_PATTERN.search(text)
        if phone_match and not updated.get("callback_number"):
            updated["callback_number"] = phone_match.group(0).replace(" ", "")

        # Doctor extraction heuristic
        doctor_match = re.search(
            r"\b(dr\.?|doctor)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", text, re.IGNORECASE
        )
        if doctor_match and not updated.get("doctor_name"):
            updated["doctor_name"] = f"Dr. {doctor_match.group(2).strip().title()}"

        return updated

    @classmethod
    def start_workflow(
        cls,
        db: Session,
        conversation: Conversation,
        initial_message: str,
        language: str = "en",
    ) -> WorkflowTurnResult:
        """Initialize appointment intake for a conversation."""
        fields = {
            "patient_name": None,
            "doctor_name": None,
            "preferred_date": None,
            "preferred_time": None,
            "callback_number": None,
            "reason": None,
        }

        # Attempt initial extraction
        fields = cls._extract_slots_from_text(initial_message, fields)

        conversation.active_workflow = "appointment_intake"
        conversation.workflow_state = {
            "step": "collecting_fields",
            "fields": fields,
            "pending_slot": None,
        }
        flag_modified(conversation, "workflow_state")
        db.flush()

        return cls._prompt_next_slot(db, conversation, language)

    @classmethod
    def handle_turn(
        cls,
        db: Session,
        conversation: Conversation,
        user_message: str,
        language: str = "en",
    ) -> WorkflowTurnResult:
        """Process an in-flight appointment intake conversation turn."""
        state = dict(conversation.workflow_state or {})
        step = state.get("step", "collecting_fields")
        fields = dict(state.get("fields", {}))

        cleaned = user_message.strip()

        # Check for user cancellation
        is_cancel = bool(
            re.search(r"\b(cancel|mansookh|abort|stop\s+booking)\b", cleaned, re.IGNORECASE)
            or (CONFIRMATION_NEGATIVE.search(cleaned) and step == "awaiting_confirmation")
        )
        if is_cancel:
            conversation.active_workflow = None
            conversation.workflow_state = None
            flag_modified(conversation, "workflow_state")
            db.flush()
            cancel_msg = {
                "ur": "آپ کی اپائنٹمنٹ کی درخواست منسوخ کر دی گئی ہے۔ میں مزید کس طرح مدد کر سکتی ہوں؟",
                "roman_ur": "Aap ki appointment request cancel kar di gayi hai. Main NovaCare ke hawale se mazeed kya madad kar sakti hoon?",
                "en": "Your appointment request has been cancelled. How else may I assist you today?",
            }.get(
                language,
                "Your appointment request has been cancelled. How else may I assist you today?",
            )
            return WorkflowTurnResult(
                response_text=cancel_msg,
                workflow_active=False,
                status="cancelled",
            )

        # If awaiting final confirmation
        if step == "awaiting_confirmation":
            if CONFIRMATION_POSITIVE.search(cleaned):
                # Save appointment request to DB with status "pending_staff_confirmation"
                appointment = AppointmentRequest(
                    conversation_id=conversation.id,
                    patient_name=fields.get("patient_name") or "Patient",
                    doctor_name=fields.get("doctor_name"),
                    department=fields.get("department"),
                    preferred_date=fields.get("preferred_date") or "Earliest Available",
                    preferred_time=fields.get("preferred_time") or "Anytime",
                    callback_number=fields.get("callback_number"),
                    reason=fields.get("reason"),
                    status="pending_staff_confirmation",
                )
                db.add(appointment)
                db.flush()

                conversation.active_workflow = None
                conversation.workflow_state = None
                flag_modified(conversation, "workflow_state")
                db.flush()

                ref_id = appointment.id[:8].upper()
                phone = fields.get("callback_number", "your number")

                if language == "ur":
                    confirmed_msg = (
                        f"✅ آپ کی اپائنٹمنٹ کی درخواست کامیابی سے درج کر لی گئی ہے (ریفرنس: #{ref_id})۔\n\n"
                        f"**حیثیت:** کلینک عملے کی تصدیق کا انتظار (Pending Staff Confirmation)\n"
                        f"نووا کیئر کا ریسیپشن عملہ ڈاکٹر کا شیڈول دیکھ کر جلد آپ کے نمبر ({phone}) پر رابطہ کر کے حتمی وقت کی تصدیق کرے گا۔"
                    )
                elif language in ("roman_ur", "mixed"):
                    confirmed_msg = (
                        f"✅ Aap ki appointment request submit ho chuki hai (Ref: #{ref_id})!\n\n"
                        f"**Status:** Pending Staff Confirmation\n"
                        f"NovaCare Medical Centre ka reception staff doctor ka calendar check kar ke jald aap ke number ({phone}) par rabta karega aur time confirm karega."
                    )
                else:
                    confirmed_msg = (
                        f"✅ Your appointment request has been submitted (Reference: #{ref_id})!\n\n"
                        f"**Status:** Pending Staff Confirmation\n"
                        f"NovaCare reception staff will review doctor availability and contact you at {phone} shortly to finalize your appointment."
                    )

                return WorkflowTurnResult(
                    response_text=confirmed_msg,
                    workflow_active=False,
                    status="confirmed",
                    appointment_id=appointment.id,
                )
            else:
                # Clarify confirmation
                prompt = {
                    "ur": "براہ کرم اپائنٹمنٹ درخواست بھیجنے کے لیے 'ہاں' (Yes) کہیں، یا منسوخ کرنے کے لیے 'نہیں' (Cancel) کہیں۔",
                    "roman_ur": "Barah-e-karam appointment submit karne ke liye 'Yes' / 'Haan' kahein, ya cancel karne ke liye 'Cancel' kahein.",
                    "en": "Please reply 'Yes' to submit your appointment request to clinic staff, or 'Cancel' to abort.",
                }.get(language, "Please reply 'Yes' to confirm or 'Cancel' to abort.")
                return WorkflowTurnResult(
                    response_text=prompt,
                    workflow_active=True,
                    status="awaiting_confirmation",
                )

        # Currently collecting fields
        pending_slot = state.get("pending_slot")
        if pending_slot and not fields.get(pending_slot):
            val = cleaned
            if pending_slot == "patient_name":
                val = re.sub(
                    r"^(the\s+patient\s+(name\s+)?is|patient\s+is|mareez\s+ka\s+naam|my\s+name\s+is)\s+",
                    "",
                    cleaned,
                    flags=re.IGNORECASE,
                ).strip()
            fields[pending_slot] = val

        # Also run extractor for additional fields mentioned
        fields = cls._extract_slots_from_text(cleaned, fields)

        conversation.workflow_state = {
            "step": "collecting_fields",
            "fields": fields,
            "pending_slot": None,
        }
        flag_modified(conversation, "workflow_state")
        db.flush()

        return cls._prompt_next_slot(db, conversation, language)

    @classmethod
    def _prompt_next_slot(
        cls,
        db: Session,
        conversation: Conversation,
        language: str,
    ) -> WorkflowTurnResult:
        """Determine next missing field and format question in appropriate language."""
        state = dict(conversation.workflow_state or {})
        fields = dict(state.get("fields", {}))

        slot_sequence = [
            (
                "patient_name",
                {
                    "en": "May I please have the patient's full name?",
                    "ur": "براہ کرم مریض کا مکمل نام بتائیے؟",
                    "roman_ur": "Barah-e-karam mareez ka mukammal naam bataiye?",
                },
            ),
            (
                "doctor_name",
                {
                    "en": "Which doctor or specialty would you like to consult (e.g. Dr. Farhan for Cardiology, Dr. Ayesha for Pediatrics, or General Physician)?",
                    "ur": "آپ کس ڈاکٹر یا شعبے میں دکھانا چاہتے ہیں؟ (مثلاً ڈاکٹر فرحان برائے امراضِ قلب، یا ڈاکٹر عائشہ برائے اطفال)",
                    "roman_ur": "Aap kis doctor ya department ko consult karna chahte hain? (Jaise Dr. Farhan Cardiology ya Dr. Ayesha Pediatrics)",
                },
            ),
            (
                "preferred_date",
                {
                    "en": "What date or day would you prefer for the appointment (e.g. tomorrow, Friday, or Oct 25)?",
                    "ur": "آپ معائنے کے لیے کس تاریخ یا دن کو ترجیح دیں گے؟",
                    "roman_ur": "Aap kis din ya tareekh ko appointment lena chahein gay?",
                },
            ),
            (
                "preferred_time",
                {
                    "en": "What time of day suits you best (e.g. Morning 11:00 AM, Evening 5:30 PM)?",
                    "ur": "آپ کے لیے دن کا کونسا وقت زیادہ مناسب رہے گا (مثلاً صبح 11 بجے یا شام 5 بجے)؟",
                    "roman_ur": "Aap ke liye konsa waqt munasib rahay ga (subah ya shaam)?",
                },
            ),
            (
                "callback_number",
                {
                    "en": "Please provide your contact phone number so our clinic staff can confirm your slot.",
                    "ur": "براہ کرم اپنا رابطہ فون نمبر فراہم کریں تاکہ عملہ وقت کی تصدیق کر سکے۔",
                    "roman_ur": "Barah-e-karam apna contact phone number faraham karein taake staff confirmation ke liye call kar sakay.",
                },
            ),
        ]

        for slot_name, prompts in slot_sequence:
            if not fields.get(slot_name):
                state["pending_slot"] = slot_name
                conversation.workflow_state = dict(state)
                flag_modified(conversation, "workflow_state")
                db.flush()
                return WorkflowTurnResult(
                    response_text=prompts.get(language, prompts["en"]),
                    workflow_active=True,
                    status="in_progress",
                )

        # All slots collected! Transition to awaiting_confirmation
        state["step"] = "awaiting_confirmation"
        state["pending_slot"] = None
        conversation.workflow_state = dict(state)
        flag_modified(conversation, "workflow_state")
        db.flush()

        p_name = fields.get("patient_name")
        d_name = fields.get("doctor_name")
        p_date = fields.get("preferred_date")
        p_time = fields.get("preferred_time")
        phone = fields.get("callback_number")

        if language == "ur":
            summary = (
                "براہ کرم اپنی اپائنٹمنٹ کی تفصیلات کی تصدیق کیجیے:\n"
                f"• مریض کا نام: {p_name}\n"
                f"• ڈاکٹر / شعبہ: {d_name}\n"
                f"• تاریخ: {p_date}\n"
                f"• وقت: {p_time}\n"
                f"• رابطہ نمبر: {phone}\n\n"
                "کیا یہ تفصیلات درست ہیں؟ تصدیق کے لیے **'ہاں'** (Yes) یا منسوخ کرنے کے لیے **'نہیں'** (Cancel) کہیں۔"
            )
        elif language in ("roman_ur", "mixed"):
            summary = (
                "Barah-e-karam apni appointment ki details confirm kijiye:\n"
                f"• Patient Name: {p_name}\n"
                f"• Doctor / Dept: {d_name}\n"
                f"• Preferred Date: {p_date}\n"
                f"• Preferred Time: {p_time}\n"
                f"• Contact Phone: {phone}\n\n"
                "Kya yeh details theek hain? Submit karne ke liye **'Yes' / 'Haan'** likhein, ya cancel karne ke liye **'Cancel'** likhein."
            )
        else:
            summary = (
                "Please confirm your appointment request details:\n"
                f"• Patient Name: {p_name}\n"
                f"• Doctor / Specialty: {d_name}\n"
                f"• Preferred Date: {p_date}\n"
                f"• Preferred Time: {p_time}\n"
                f"• Contact Phone: {phone}\n\n"
                "Are these details correct? Reply **'Yes'** to submit to clinic reception, or **'Cancel'** to withdraw."
            )

        return WorkflowTurnResult(
            response_text=summary,
            workflow_active=True,
            status="awaiting_confirmation",
        )

    @staticmethod
    def cancel_appointment(
        db: Session,
        conversation_id: str,
        reason: str | None = None,
    ) -> AppointmentRequest | None:
        """Find latest active appointment request for conversation and mark cancelled."""
        stmt = (
            select(AppointmentRequest)
            .where(
                AppointmentRequest.conversation_id == conversation_id,
                AppointmentRequest.status.in_(
                    ["draft", "pending_staff_confirmation", "confirmed_by_staff", "reviewed"]
                ),
            )
            .order_by(AppointmentRequest.created_at.desc())
        )
        appointment = db.scalars(stmt).first()
        if appointment:
            appointment.status = "cancelled"
            if reason:
                appointment.reason = f"{appointment.reason or ''} [Cancelled: {reason}]".strip()
            db.flush()
        return appointment
