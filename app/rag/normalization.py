"""Text normalization, script detection, and tokenization for multilingual RAG."""

import re
import unicodedata

from app.rag.schemas import LanguageLabel

# Urdu diacritics / tashkeel regex
URDU_DIACRITICS_PATTERN = re.compile(
    r"[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]"
)

# Arabic to Urdu character mapping
URDU_CHAR_MAP = {
    "\u0643": "\u06a9",  # Arabic Kaf ك -> Urdu Keheh ک
    "\u064a": "\u06cc",  # Arabic Yeh ي -> Urdu Farsi Yeh ی
    "\u0649": "\u06cc",  # Alef Maksura ى -> Urdu Farsi Yeh ی
    "\u0647": "\u06c1",  # Arabic Heh ه -> Urdu Heh Goal ہ
    "\u0629": "\u06c1",  # Teh Marbuta ة -> Urdu Heh Goal ہ
    "\u0640": "",  # Tatweel / Kashida -> remove
}

# Common Roman Urdu stopwords / functional markers for detection
ROMAN_URDU_MARKERS = {
    "kya",
    "hai",
    "hain",
    "ki",
    "ka",
    "ke",
    "ko",
    "se",
    "me",
    "mein",
    "par",
    "kab",
    "kitna",
    "kitni",
    "kitne",
    "kahan",
    "kese",
    "kaise",
    "hoga",
    "hogi",
    "honge",
    "chahiye",
    "aur",
    "bhi",
    "yeh",
    "woh",
    "kuch",
    "ap",
    "aap",
    "meri",
    "mera",
    "mere",
    "unka",
    "unki",
    "unke",
    "konsa",
    "kounsa",
    "konsi",
    "wali",
    "wale",
    "wala",
    "hota",
    "hoti",
    "raha",
    "rahi",
    "rahe",
    "skta",
    "sakta",
    "sakti",
    "sakte",
    "karein",
    "karen",
    "bataen",
    "bataiye",
    "batao",
    "madad",
    "chahye",
    "mil",
    "mujhe",
    "hum",
    "humein",
    "kis",
    "din",
    "baithti",
    "baithte",
    "hotay",
}

# English grammatical and functional markers (excluding loanword nouns like clinic, doctor, fee)
ENGLISH_FUNCTIONAL_MARKERS = {
    "what",
    "is",
    "are",
    "the",
    "in",
    "on",
    "at",
    "for",
    "with",
    "about",
    "when",
    "where",
    "who",
    "which",
    "how",
    "can",
    "could",
    "would",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "will",
    "shall",
    "should",
    "please",
    "tell",
    "show",
    "give",
    "available",
    "closed",
    "open",
    "cost",
    "much",
    "many",
    "prefer",
    "preferably",
    "evening",
    "morning",
}

# Conservative Roman Urdu vocabulary expansion / normalization aliases
# Mapping common colloquial variants to standard canonical search terms
ROMAN_URDU_ALIASES: dict[str, list[str]] = {
    "fees": ["fee", "charges", "pkr"],
    "fee": ["charges", "fees", "pkr"],
    "charges": ["fee", "fees", "pkr"],
    "paisa": ["fee", "charges", "pkr"],
    "paise": ["fee", "charges", "pkr"],
    "timings": ["timing", "hours", "schedule", "auqat", "waqt"],
    "timing": ["timings", "hours", "schedule", "auqat", "waqt"],
    "auqat": ["timings", "hours", "schedule", "waqt"],
    "waqt": ["timings", "hours", "schedule", "auqat"],
    "hours": ["timings", "schedule", "timing"],
    "kab": ["when", "timing", "schedule", "hours"],
    "khula": ["open", "hours", "timings"],
    "khuli": ["open", "hours", "timings"],
    "band": ["closed", "off", "holiday"],
    "chutti": ["holiday", "closed", "off"],
    "appointment": ["booking", "consultation", "mulaqat"],
    "booking": ["appointment", "consultation"],
    "mulaqat": ["appointment", "consultation"],
    "doctor": ["dr", "physician", "specialist"],
    "dr": ["doctor"],
    "daktar": ["doctor", "dr"],
    "dakdar": ["doctor", "dr"],
    "pata": ["address", "location"],
    "kahan": ["where", "location", "address"],
    "address": ["location", "pata"],
    "rabta": ["contact", "phone", "number"],
    "phone": ["number", "contact", "rabta"],
    "bache": ["pediatrics", "child", "children"],
    "bachon": ["pediatrics", "child", "children"],
    "dil": ["cardiology", "heart"],
    "jild": ["dermatology", "skin"],
    "haddi": ["orthopedics", "bone"],
    "haddiyon": ["orthopedics", "bone"],
}


def normalize_unicode(text: str) -> str:
    """Normalize Unicode characters to NFKC and standardize spacing."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    # Replace multiple spaces, non-breaking spaces, and tabs with a single space
    normalized = re.sub(r"[\s\u00A0\u200B\u200E\u200F]+", " ", normalized)
    return normalized.strip()


def normalize_urdu(text: str) -> str:
    """Standardize Urdu script characters and strip diacritics."""
    if not text:
        return ""
    # Map Arabic variants to Urdu
    result = []
    for char in text:
        result.append(URDU_CHAR_MAP.get(char, char))
    standardized = "".join(result)
    # Remove diacritics/tashkeel
    cleaned = URDU_DIACRITICS_PATTERN.sub("", standardized)
    return normalize_unicode(cleaned)


def detect_language_script(text: str) -> LanguageLabel:
    """Detect whether text is predominantly English, Urdu script, Roman Urdu, or Mixed."""
    cleaned = normalize_unicode(text)
    if not cleaned:
        return "unknown"

    # Count Urdu / Arabic characters vs Latin characters
    urdu_chars = sum(
        1
        for c in cleaned
        if "\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f" or "\ufb50" <= c <= "\ufdff"
    )
    latin_chars = sum(1 for c in cleaned if ("a" <= c <= "z") or ("A" <= c <= "Z"))

    total_alpha = urdu_chars + latin_chars
    if total_alpha == 0:
        return "unknown"

    # Strong Urdu script presence
    if urdu_chars / total_alpha >= 0.35:
        if latin_chars > 3:
            return "mixed"
        return "ur"

    # Latin text analysis (English vs Roman Urdu vs Mixed)
    words = re.findall(r"\b[a-zA-Z]+\b", cleaned.lower())
    if not words:
        return "unknown"

    roman_urdu_count = sum(1 for w in words if w in ROMAN_URDU_MARKERS)
    english_count = sum(1 for w in words if w in ENGLISH_FUNCTIONAL_MARKERS)

    # English content words that indicate mixed code-switching when paired with Roman Urdu
    mixed_content_words = {
        "consultation",
        "cardiologist",
        "dermatologist",
        "pediatrician",
        "specialist",
        "qualifications",
        "insurance",
        "emergency",
        "preferably",
        "cardiology",
        "dermatology",
        "pediatrics",
    }
    has_mixed_content = any(w in mixed_content_words for w in words)

    # Mixed check: contains both Roman Urdu markers and English functional or clinical terms
    if roman_urdu_count > 0 and (english_count > 0 or has_mixed_content):
        return "mixed"

    # Check for English query
    if english_count > 0 and roman_urdu_count == 0:
        return "en"

    # Check for Roman Urdu
    if roman_urdu_count > 0 and english_count == 0:
        return "roman_ur"

    # Heuristic for short queries with English vocabulary
    common_english_vocab = {
        "clinic",
        "doctor",
        "dr",
        "appointment",
        "consultation",
        "fee",
        "fees",
        "timings",
        "hours",
        "hospital",
        "service",
        "services",
        "location",
        "address",
        "emergency",
        "pediatrician",
        "cardiology",
        "dermatology",
    }
    english_vocab_count = sum(1 for w in words if w in common_english_vocab)

    if english_vocab_count > 0 and roman_urdu_count == 0:
        return "en"

    return "en" if latin_chars > 0 else "unknown"


def expand_query_aliases(query: str) -> str:
    """Non-destructively append recognized synonym terms to query for enhanced BM25 matching."""
    cleaned = normalize_unicode(query).lower()
    tokens = re.findall(r"\b[\w]+\b", cleaned)
    expansions = set()

    for token in tokens:
        if token in ROMAN_URDU_ALIASES:
            for alias in ROMAN_URDU_ALIASES[token]:
                if alias not in tokens:
                    expansions.add(alias)

    if expansions:
        return f"{query} {' '.join(sorted(expansions))}"
    return query


# Minimal stopwords (pure functional particles) filtered from BM25 to avoid noise matching
BM25_FUNCTIONAL_STOPWORDS = {
    # English functional particles
    "is",
    "are",
    "the",
    "a",
    "an",
    "in",
    "on",
    "at",
    "for",
    "with",
    "about",
    "to",
    "from",
    "by",
    "of",
    "and",
    "or",
    "your",
    "my",
    "our",
    "can",
    "you",
    "me",
    "do",
    "does",
    "did",
    "have",
    "has",
    "it",
    # Urdu functional particles
    "کے",
    "کی",
    "کا",
    "کو",
    "سے",
    "میں",
    "پر",
    "ہے",
    "ہیں",
    "اور",
    "بھی",
    "یہ",
    "وہ",
    "آپ",
    "اپ",
    "پاس",
    "کیا",
    "ایک",
    "تک",
    "نے",
}


def tokenize_for_bm25(text: str) -> list[str]:
    """Unicode-aware tokenization supporting English, Urdu, and Roman Urdu."""
    cleaned = normalize_urdu(text)
    # Tokenize word characters including Urdu and Latin
    tokens = re.findall(r"[\w]+", cleaned.lower())
    # Filter out pure functional particles and single characters
    return [t for t in tokens if len(t) > 1 and t not in BM25_FUNCTIONAL_STOPWORDS]
