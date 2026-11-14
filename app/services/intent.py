"""Intent classification and language detection for incoming messages."""

import re
from dataclasses import dataclass

from app.rag.normalization import detect_language_script

GREETING_PATTERNS = [
    r"^(hi|hello|hey|salam|assalam\s*o?\s*alaikum|aOA|good\s+morning|good\s+evening|adaab)\b",
]

APPOINTMENT_BOOKING_PATTERNS = [
    r"\b(book|schedule|make|take|get|need|want)\s+(an?\s+)?appointment\b",
    r"\bappointment\s+(book|schedule|chahiye|lena|leni|krwana|karwana)\b",
    r"\bdoctor\s+(ko\s+dikhana|se\s+milna|checkup\s+karwana)\b",
    r"\b(book|schedule)\s+(a\s+)?consultation\b",
]

APPOINTMENT_CANCEL_PATTERNS = [
    r"\bcancel\s+(my\s+)?appointment\b",
    r"\bappointment\s+cancel\b",
    r"\bappointment\s+mansookh\b",
]

HANDOFF_PATTERNS = [
    r"\b(talk|speak|connect)\s+(to|with|me\s+to)\s+(a\s+)?(human|person|agent|staff|receptionist|someone)\b",
    r"\b(insan|staff|receptionist)\s+se\s+baat\b",
    r"\bhuman\s+(support|staff|receptionist|help)\b",
    r"\brepresentative\b",
    r"\bcall\s+me\b",
]


@dataclass
class IntentResult:
    """Classified intent with confidence and detected language."""

    intent: str  # greeting, appointment_booking, appointment_cancel, handoff_request, clinic_faq, general
    language: str  # en, ur, roman_ur, mixed


def _matches_any(text: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def classify_intent(text: str) -> IntentResult:
    """Classify the user query intent and detect the query language.

    Args:
        text: Raw user message.

    Returns:
        IntentResult containing normalized intent and language code.
    """
    cleaned = text.strip()
    language = detect_language_script(cleaned)

    if _matches_any(cleaned, APPOINTMENT_CANCEL_PATTERNS):
        return IntentResult(intent="appointment_cancel", language=language)

    if _matches_any(cleaned, HANDOFF_PATTERNS):
        return IntentResult(intent="handoff_request", language=language)

    if _matches_any(cleaned, APPOINTMENT_BOOKING_PATTERNS):
        return IntentResult(intent="appointment_booking", language=language)

    if _matches_any(cleaned, GREETING_PATTERNS) and len(cleaned.split()) <= 4:
        return IntentResult(intent="greeting", language=language)

    # If it is an informational question or clinic inquiry
    return IntentResult(intent="clinic_faq", language=language)
