"""Deterministic medical safety guardrails for Aevora AI."""

import re
from dataclasses import dataclass

EMERGENCY_KEYWORDS_EN = [
    r"\bchest\s+pain\b",
    r"\bheart\s+attack\b",
    r"\bstroke\b",
    r"\bunconscious\b",
    r"\bcan't\s+breathe\b",
    r"\bcannot\s+breathe\b",
    r"\bshortness\s+of\s+breath\b",
    r"\bsevere\s+bleeding\b",
    r"\bheavy\s+bleeding\b",
    r"\bpoisoning\b",
    r"\bpoisoned\b",
    r"\bchoking\b",
    r"\bseizure\b",
    r"\bsuicide\b",
    r"\bsuicidal\b",
    r"\boverdose\b",
]

EMERGENCY_KEYWORDS_UR = [
    r"سینے\s+میں\s+درد",
    r"دل\s+کا\s+دورہ",
    r"سانس\s+نہیں\s+آ\s+رہا",
    r"سانس\s+لینے\s+میں\s+شدید\s+تکلیف",
    r"بے\s*ہوش",
    r"شدید\s+خون",
    r"زہر",
    r"ہنگامی\s+حالت",
]

EMERGENCY_KEYWORDS_ROMAN = [
    r"\bseene\s+me(in)?\s+dard\b",
    r"\bdil\s+ka\s+daura\b",
    r"\bsans\s+(nahi|nhi)\s+aa\s+rah[ai]\b",
    r"\bbehosh\b",
    r"\bshadeed\s+khoon\b",
    r"\bemergency\b",
    r"\bzahar\b",
    r"\bchhattee\s+me\s+dard\b",
]

CLINICAL_ADVICE_KEYWORDS_EN = [
    r"\bdiagnos(e|is)\b",
    r"\bwhat\s+(medicine|medication|drug|pill|syrup|antibiotic)\s+(should|can)\s+i\s+take\b",
    r"\b(dosage|dose)\s+(of|for)\b",
    r"\bprescribe\b",
    r"\bprescription(\s+for)?\b",
    r"\bwhat\s+illness\s+do\s+i\s+have\b",
    r"\bwhat\s+disease\s+do\s+i\s+have\b",
    r"\bcure\s+my\b",
    r"\btreat\s+my\b",
    r"\bmedical\s+advice\b",
]

CLINICAL_ADVICE_KEYWORDS_UR = [
    r"تشخیص",
    r"کونسی\s+دوا",
    r"کون\s*سی\s+دوا",
    r"دوا\s+کھانی\s+چاہیے",
    r"دوا\s+کھاؤں",
    r"کونسی\s+گولی",
    r"کون\s*سی\s+گولی",
    r"نسخہ\s+لکھ\s+دیں",
    r"علاج\s+بتائیں",
    r"مجھے\s+کیا\s+بیماری\s+ہے",
]

CLINICAL_ADVICE_KEYWORDS_ROMAN = [
    r"\bkonsi\s+(dawa|dawai|goli|tablet)\s+(khau|khaon|lu|loon|len)\b",
    r"\bilaj\s+bata(yein|o|ein)\b",
    r"\bmujhe\s+kya\s+bimari\s+hai\b",
    r"\bprescription\s+de\s+(do|dein)\b",
    r"\btashkhees\b",
]


@dataclass
class SafetyCheckResult:
    """Result of deterministic safety evaluation."""

    is_safe: bool
    violation_type: str | None  # "emergency", "clinical_advice", None
    response_message: str | None
    requires_handoff: bool


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


COMPILED_EMERGENCY = _compile_patterns(
    EMERGENCY_KEYWORDS_EN + EMERGENCY_KEYWORDS_UR + EMERGENCY_KEYWORDS_ROMAN
)
COMPILED_CLINICAL = _compile_patterns(
    CLINICAL_ADVICE_KEYWORDS_EN + CLINICAL_ADVICE_KEYWORDS_UR + CLINICAL_ADVICE_KEYWORDS_ROMAN
)


def evaluate_safety(text: str, language: str = "en") -> SafetyCheckResult:
    """Evaluate whether user input contains medical emergencies or requests for clinical advice.

    Args:
        text: Input text from the user.
        language: Detected or preferred language code ('en', 'ur', 'roman_ur', 'mixed').

    Returns:
        SafetyCheckResult with safety status and appropriate localized guidance.
    """
    cleaned = text.strip()

    # 1. Check for Emergency
    for pattern in COMPILED_EMERGENCY:
        if pattern.search(cleaned):
            if language == "ur":
                msg = (
                    "⚠️ **ہنگامی الرٹ:** اگر یہ جان لیوا صورتحال یا فوری طبی ایمرجنسی ہے تو "
                    "براہ کرم فوراً 1122 پر کال کریں یا قریبی ایمرجنسی ہسپتال تشریف لے جائیں۔ "
                    "نووا کیئر میڈیکل سینٹر کا ورچوئل اسسٹنٹ ہنگامی طبی امداد فراہم کرنے کا مجاز نہیں ہے۔"
                )
            elif language in ("roman_ur", "mixed"):
                msg = (
                    "⚠️ **Emergency Alert:** Agar yeh fori tibbi emergency hai toh barah-e-karam "
                    "foran **1122** par call karein ya qareebi emergency room tashreef le jayein. "
                    "NovaCare Medical Centre ka virtual assistant emergency halaat handle nahi kar sakta."
                )
            else:
                msg = (
                    "⚠️ **Emergency Alert:** If you or someone else is experiencing a life-threatening medical "
                    "emergency, please immediately call **1122** (Emergency Rescue) or proceed to the nearest emergency "
                    "room. NovaCare's virtual receptionist cannot manage acute medical emergencies."
                )
            return SafetyCheckResult(
                is_safe=False,
                violation_type="emergency",
                response_message=msg,
                requires_handoff=True,
            )

    # 2. Check for Clinical Advice / Diagnosis / Prescription
    for pattern in COMPILED_CLINICAL:
        if pattern.search(cleaned):
            if language == "ur":
                msg = (
                    "میں نووا کیئر میڈیکل سینٹر کی ورچوئل ریسیپشنسٹ، ایوورا (Aevora) ہوں۔ "
                    "میں کلینک کے اوقات، ڈاکٹرز کے شیڈول اور اپائنٹمنٹ بکنگ میں مدد کر سکتی ہوں، "
                    "لیکن میں طبی تشخیص، علاج کے مشورے یا ادویات تجویز نہیں کر سکتی۔ "
                    "کیا آپ متعلقہ ڈاکٹر سے معائنے کے لیے اپائنٹمنٹ کا وقت لینا چاہتے ہیں؟"
                )
            elif language in ("roman_ur", "mixed"):
                msg = (
                    "Main NovaCare Medical Centre ki virtual receptionist, Aevora hoon. "
                    "Main clinic timings, doctor schedules aur appointment requests mein madad kar sakti hoon, "
                    "lekin main koi tibbi tashkhees (diagnosis), ilaaj ka mashwara ya medicines prescribe nahi kar sakti. "
                    "Kya aap mutalliqah doctor ke sath appointment schedule karwana chahein gay?"
                )
            else:
                msg = (
                    "I am Aevora, the virtual receptionist for NovaCare Medical Centre. "
                    "I can help with clinic hours, doctor schedules, service fees, and appointment bookings, "
                    "but I cannot provide medical diagnoses, treatment recommendations, or prescriptions. "
                    "Would you like me to help schedule a consultation with one of our physicians?"
                )
            return SafetyCheckResult(
                is_safe=False,
                violation_type="clinical_advice",
                response_message=msg,
                requires_handoff=False,
            )

    return SafetyCheckResult(
        is_safe=True,
        violation_type=None,
        response_message=None,
        requires_handoff=False,
    )
