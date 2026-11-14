"""Centralized and security-conscious logging configuration for Aevora AI."""

import logging
import re
import sys

# Regex patterns for common secrets and sensitive parameters to sanitize
SENSITIVE_PATTERNS = [
    (
        re.compile(
            r"(api[-_]?key\s*[:=]\s*)['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(
            r"(access[-_]?token\s*[:=]\s*)['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"(bearer\s+)([A-Za-z0-9_\-\.]{8,})", re.IGNORECASE),
        r"\1[REDACTED]",
    ),
    (
        re.compile(
            r"(app[-_]?secret\s*[:=]\s*)['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(
            r"(verify[-_]?token\s*[:=]\s*)['\"]?([A-Za-z0-9_\-\.]{4,})['\"]?",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"(\b03\d{2}|\+?923\d{2})\d{4}(\d{3}\b)"),
        r"\1****\2",
    ),
]


class SensitiveDataSanitizingFilter(logging.Filter):
    """Logging filter that scrubs tokens, secrets, and credentials from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            sanitized = record.msg
            for pattern, replacement in SENSITIVE_PATTERNS:
                sanitized = pattern.sub(replacement, sanitized)
            record.msg = sanitized
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure centralized root logging with formatting and security filtering."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    handler.setFormatter(logging.Formatter(fmt=log_format, datefmt=date_format))
    handler.addFilter(SensitiveDataSanitizingFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retrieve an application logger with standard security sanitization."""
    return logging.getLogger(name)
