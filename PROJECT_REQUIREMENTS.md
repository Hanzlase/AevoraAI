# Aevora AI — Project Requirements Document (PRD)

> **Document Version**: 1.0.0  
> **Status**: Approved Baseline  
> **Product**: Aevora AI  
> **Tagline**: Healthcare conversations, made human.  
> **Target Demographic**: Patients and clinic staff interacting via WhatsApp in English, Urdu, and Roman Urdu.

---

## 1. Product Purpose & Intended Users

### 1.1 Purpose
Aevora AI is an enterprise-grade AI-powered clinic receptionist designed to bridge the gap between healthcare facilities and their patients via WhatsApp. By automating repetitive administrative inquiries, doctor discovery, schedule checks, fee lookups, and appointment intake, Aevora AI frees clinic staff to concentrate on in-person patient care while providing patients with instant, 24/7 answers in their natural language of choice.

### 1.2 Target Users
- **Patients**: Existing or prospective patients seeking clinic hours, doctor specialties, consultation charges, service details, and appointment booking or rescheduling.
- **Clinic Administrative Staff**: Receptionists and practice managers who review appointment intakes, receive complex escalations, and handle clinical handoffs.
- **Hiring Assessment Demonstrators & Evaluators**: Engineers evaluating system reliability, code architecture, security posture, and grounding rigor.

### 1.3 Demo Scenario: NovaCare Medical Centre
All clinic details in this project represent **NovaCare Medical Centre**, a **fictional** private healthcare facility used strictly for software testing and evaluation:
- **Location**: Fictional medical complex.
- **Departments**: General Medicine, Pediatrics, Dermatology, Cardiology, Gynecology, Orthopedics, and Diagnostic Radiology.
- **Source Documents**: `NovaCare_Medical_Centre_RAG_Knowledge_Base.pdf` and `NovaCare_RAG_Source_of_Truth.json`.

> [!IMPORTANT]
> **Fictional Clinic Dataset Disclaimer**: All doctor names, room numbers, consultation fees, test packages, and operational policies are synthetic data created exclusively for benchmark evaluation. They must never be presented as real clinical facts.

---

## 2. Functional Scope (Complete MVP)

### 2.1 Clinic Administration & Knowledge Retrieval
- **Clinic FAQ**: Answers questions regarding operating hours, parking, wheelchair access, payment modes, laboratory timings, and pharmacy locations.
- **Doctor Directory**: Provides doctor specialties, degrees, languages spoken, clinic room numbers, and OPD consultation days/times.
- **Services & Fee Lookups**: Delivers transparent consultation fees, diagnostic test pricing, and procedure packages strictly grounded in the approved clinic knowledge base.

### 2.2 Multilingual Natural Language Understanding
- Full conversational capabilities in **English**, **Urdu** (Arabic script), and **Roman Urdu** (Urdu transliterated into Latin characters).
- Automatic language detection and smooth switching without requiring manual user toggles.
- Proper handling of code-mixed inputs (e.g., mixing English medical terms within Roman Urdu syntax).

### 2.3 Grounded Retrieval-Augmented Generation (RAG)
- Answers derived strictly from the approved NovaCare clinic documents.
- Refusal mechanism for out-of-domain, non-clinic, or missing information ("honest unknown" answers without hallucination).
- Traceable source metadata tracking (document page numbers and sections).

### 2.4 Multimodal Voice Support
- Inbound voice note ingestion from WhatsApp (`.ogg` Opus audio).
- Automated transcription to text using local CPU/GPU Faster-Whisper.
- Multilingual voice replies generated via lightweight Edge TTS, alongside full text responses for accessibility.

### 2.5 Reception Workflows
- **Appointment Request Intake**: Collects patient name, contact number, preferred doctor/specialty, preferred date/time slot, and reason for visit.
- **Status Integrity**: Strictly informs patients that requests are "Pending Staff Confirmation" and never fabricates confirmed appointment slots.
- **Modifications & Cancellations**: Collects requests to reschedule or cancel existing bookings.
- **Staff Handoff**: Flags uncertain, frustrated, or complex non-standard requests for human receptionist takeover.

---

## 3. Clinical Safety & Operational Boundaries

### 3.1 Strict Non-Clinical Scope
- **No Medical Diagnosis**: Under no circumstances does Aevora AI evaluate symptoms or offer differential diagnoses.
- **No Medication Advice or Prescriptions**: Will never recommend, adjust, or comment on drug dosages or active pharmaceutical treatments.
- **Emergency Escalation**: Immediate emergency keyword detection (e.g., chest pain, difficulty breathing, profuse bleeding, stroke symptoms) triggers a pre-configured urgent safety message instructing the patient to call emergency services or visit the nearest emergency room immediately.

### 3.2 Privacy & Data Minimization
- Never requests national identification numbers, credit card details, or unnecessary sensitive medical history.
- Zero credential logging: API keys, access tokens, and webhook verification tokens are never logged or returned by endpoints.
- Message logging is sanitized to exclude full sensitive personal identifiable information (PII).

---

## 4. Non-Goals (Out of Scope for MVP)

1. **No Live EHR / EMR Integration**: No direct connection to Epic, Cerner, Kareo, or proprietary electronic health records.
2. **No Real-Time Calendar Slot Locking**: Does not connect to live doctor Google Calendars or clinic management software; all bookings are intakes submitted for staff confirmation.
3. **No Emergency Triage**: Does not triage medical acuity or replace emergency dispatch services.
4. **No Paid Cloud Infrastructure by Default**: Architecture prioritizes free/open-source components (SQLite, CPU embeddings, FAISS, Cloudflare Quick Tunnel) avoiding unnecessary AWS, Azure, Pinecone, or Redis subscriptions.

---

## 5. Non-Functional Requirements

| Requirement | Target Metric / Guideline |
| :--- | :--- |
| **Response Latency** | Text RAG responses: < 3.0s; Voice note transcription: < 5.0s on standard CPU |
| **Grounding Precision** | 100% adherence to source knowledge base without ungrounded fact generation |
| **Maintainability** | Clean modular monolith with clear domain encapsulation |
| **Reliability** | Webhook idempotency preventing duplicate WhatsApp event processing |
| **Testability** | High test coverage with simulated offline fixtures (no live API keys required) |
| **Security** | Pydantic SecretStr protection, SHA-256 HMAC webhook signature verification |
