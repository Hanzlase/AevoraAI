"""Tests for deterministic medical safety and triage guardrails."""

import pytest

from app.ai.safety import evaluate_safety


@pytest.mark.parametrize(
    "query,lang",
    [
        ("I am having severe chest pain and cannot breathe", "en"),
        ("Patient had a sudden heart attack and is unconscious", "en"),
        ("میرے سینے میں شدید درد ہو رہا ہے اور سانس نہیں آ رہا", "ur"),
        ("seene me shadeed dard hai aur sans nhi aa raha", "roman_ur"),
        ("patient behosh ho gaya hai foran madad karein", "roman_ur"),
    ],
)
def test_emergency_redirection_triggered(query: str, lang: str):
    result = evaluate_safety(query, language=lang)
    assert not result.is_safe
    assert result.violation_type == "emergency"
    assert result.requires_handoff is True
    assert "1122" in result.response_message


@pytest.mark.parametrize(
    "query,lang",
    [
        ("What medicine should I take for high blood pressure?", "en"),
        ("Can you diagnose this skin rash on my arm?", "en"),
        ("مجھے کونسی دوا کھانی چاہیے؟", "ur"),
        ("konsi goli khau blood pressure ke liye", "roman_ur"),
        ("mujhe ilaj batao aur prescription de do", "roman_ur"),
    ],
)
def test_clinical_advice_deflection(query: str, lang: str):
    result = evaluate_safety(query, language=lang)
    assert not result.is_safe
    assert result.violation_type == "clinical_advice"
    assert result.requires_handoff is False
    assert (
        "cannot provide medical diagnoses" in result.response_message.lower()
        or "تشخیص" in result.response_message
        or "tashkhees" in result.response_message.lower()
    )


@pytest.mark.parametrize(
    "query,lang",
    [
        ("What are NovaCare clinic timings on Monday?", "en"),
        ("When is Dr. Farhan available for consultation?", "en"),
        ("ڈاکٹر عائشہ کی فیس کتنی ہے؟", "ur"),
        ("Cardiology department ki consultation fee kitni hai?", "roman_ur"),
        ("Clinic ka address kahan par hai?", "roman_ur"),
    ],
)
def test_safe_clinic_queries_pass(query: str, lang: str):
    result = evaluate_safety(query, language=lang)
    assert result.is_safe is True
    assert result.violation_type is None
    assert result.response_message is None
    assert result.requires_handoff is False
