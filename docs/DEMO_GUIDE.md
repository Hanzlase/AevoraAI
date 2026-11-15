# Aevora AI — Employer Demonstration Guide

This guide provides a structured 5–10 minute demonstration script showcasing Aevora AI's capabilities as an enterprise-grade multilingual WhatsApp clinic receptionist for NovaCare Medical Centre.

---

## 1. Demonstration Setup & Pre-Flight Checklist

1. **Start the Application**:
   ```powershell
   .\scripts\start_windows.ps1
   ```
2. **Open the Staff Dashboard in Browser**:
   - URL: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
   - Credentials: `admin` / `NovaCare2026!`
3. **Verify Health Endpoint**:
   - URL: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) $\rightarrow$ Returns `"status": "healthy"`.

---

## 2. Step-by-Step Demonstration Script (5–10 Minutes)

### Phase A: Executive Introduction (1 Minute)
- **Narrative**:
  > *"Aevora AI is a multilingual WhatsApp clinic receptionist built for healthcare facilities. Today we are demonstrating it on our demo clinic, NovaCare Medical Centre. It handles patient inquiries, doctor schedules, fees, multi-turn appointment bookings, and voice notes across English, Urdu script, and Roman Urdu—while strictly enforcing medical safety guardrails to ensure it never diagnoses or prescribes."*

---

### Phase B: Multilingual Clinic Grounding (2 Minutes)

#### Step 1: English Clinic Inquiry
- **Action**: Send chat request via Web or curl:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"message": "What are your cardiology OPD timings and doctor consultation fees?"}'
  ```
- **Expected Outcome**:
  - Assistant responds with Dr. Bilal Ahmed's cardiology OPD timings (Monday, Tuesday, Thursday 5:00 PM – 8:00 PM) and exact consultation fee (PKR 4,500).
  - Highlights retrieved source citations internally.

#### Step 2: Roman Urdu Inquiry & Language Matching
- **Action**:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"message": "Dr Farhan ki timing kya hai aur clinic kahan par waqia hai?"}'
  ```
- **Expected Outcome**:
  - Assistant naturally responds in **Roman Urdu** matching the patient's phrasing.
  - Answers with Dr. Farhan's general medicine timings and F-7 Markaz clinic location.

#### Step 3: Urdu Script Inquiry
- **Action**:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"message": "نووا کیئر کلینک کا پتہ اور رابطہ نمبر کیا ہے؟"}'
  ```
- **Expected Outcome**:
  - Assistant responds in **Urdu script** with correct clinic address and phone number (`+92 51 844 9100`).

---

### Phase C: Progressive Appointment Intake & Staff Review (2 Minutes)

#### Step 4: Initiate Appointment Booking
- **Action**:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"message": "I would like to book an appointment with Dr. Farhan"}'
  ```
- **Expected Outcome**:
  - Assistant activates the appointment intake state machine.
  - Asks for patient's full name.

#### Step 5: Complete Slots & Explicit Confirmation
- **Action**: Submit patient name, preferred date, time, and callback phone number across successive turns. When the assistant presents the summary:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"conversation_id": "<CONV_ID>", "message": "Yes, please confirm"}'
  ```
- **Expected Outcome**:
  - Assistant returns: `Status: Pending Staff Confirmation`.
  - Explains that receptionist staff will confirm the slot with the doctor.
  - **Key Note to Highlight**: Aevora never falsely claims an appointment is directly booked into a clinical EMR without human staff review.

#### Step 6: Review in Staff Dashboard
- **Action**: Switch to browser at `http://127.0.0.1:8000/dashboard` and click **Appointments**.
- **Demonstrate**:
  - Patient's intake request appears immediately in the table.
  - Click **Confirm** button $\rightarrow$ updates status to `Confirmed by Staff`.

---

### Phase D: Human Staff Escalation & Triage (1 Minute)

#### Step 7: Patient Requests Human Staff
- **Action**:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"message": "Please connect me to human staff, I need help from a real person."}'
  ```
- **Expected Outcome**:
  - Assistant politely confirms the escalation: *"I have connected your request with our human reception desk at NovaCare Medical Centre."*
- **Action in Dashboard**:
  - Navigate to **Staff Handoffs** in the dashboard.
  - Show the new pending escalation record.
  - Click **Take Over** (`in_progress`) and then **Resolve**.

---

### Phase E: Deterministic Medical Guardrails (1 Minute)

#### Step 8: Prescription & Diagnosis Deflection
- **Action**:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"message": "What dosage of amoxicillin antibiotic should I take for my tooth infection?"}'
  ```
- **Expected Outcome**:
  - Assistant strictly refuses clinical prescription: *"I cannot prescribe medications or provide clinical diagnoses. Would you like me to connect you with a doctor for an in-person consultation?"*

#### Step 9: Acute Emergency Redirection
- **Action**:
  ```powershell
  curl -X POST "http://127.0.0.1:8000/api/v1/chat" `
       -H "Content-Type: application/json" `
       -d '{"message": "Severe crushing chest pain, difficulty breathing, and patient is sweating heavily"}'
  ```
- **Expected Outcome**:
  - Immediate redirection to **1122** (Emergency Rescue).
  - Automatically creates a priority escalation record in the staff dashboard.

---

### Phase F: Architecture & Engineering Wrap-Up (1 Minute)
- **Highlights**:
  - **Zero-cost stack**: Runs on Windows locally with SQLite and FAISS CPU.
  - **RAG Architecture**: Hybrid Dense (E5-small) + Sparse (BM25Okapi) fusion with Reciprocal Rank Fusion ($k=60$).
  - **WhatsApp & Voice**: Meta Cloud API webhooks with HMAC-SHA256 validation, durable event queue idempotency, and Faster-Whisper transcription.
  - **Test Suite**: 105 automated unit and integration tests passing with 100% green status.

---

## 3. Alternative Offline / Mock Demonstration Path

If external internet or Meta credentials are not configured:
- Set `WHATSAPP_ENABLED=false` and run the automated test suite:
  ```powershell
  .\scripts\run_tests.ps1
  ```
- All WhatsApp webhook parsing, HMAC validation, durable event queuing, audio conversion, and Whisper transcription run deterministically against the mock test harness without external API dependencies.
