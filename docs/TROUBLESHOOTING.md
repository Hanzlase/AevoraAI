# Aevora AI — Diagnostics & Troubleshooting Guide

This guide covers common operational, integration, and runtime issues encountered when running Aevora AI, along with verified diagnostic steps and solutions.

---

## 1. Webhook & Tunnel Issues

### Issue 1.1: Webhook GET Verification Returns 403 Forbidden
- **Symptoms**: Meta Developer Console shows red alert: *"The URL couldn't be validated."*
- **Cause**: The `hub.verify_token` sent by Meta does not match `WEBHOOK_VERIFY_TOKEN` configured in `.env`.
- **Solution**:
  1. Check `.env` for `WEBHOOK_VERIFY_TOKEN` (ensure no leading/trailing whitespace).
  2. Ensure the exact same string is pasted into Meta's *Verify Token* field.
  3. Verify the server is running on `127.0.0.1:8000`.

### Issue 1.2: Webhook POST Returns 403 Forbidden (Signature Mismatch)
- **Symptoms**: Incoming WhatsApp messages trigger log warning: `Rejecting webhook notification: X-Hub-Signature-256 mismatch.`
- **Cause**: `META_APP_SECRET` does not match the secret of the Meta App that generated the webhook.
- **Solution**:
  1. Open Meta Developer Dashboard $\rightarrow$ **App settings** $\rightarrow$ **Basic**.
  2. Click *Show* next to **App Secret** and copy it.
  3. Paste it into `META_APP_SECRET` in `.env` and restart the application.

### Issue 1.3: Cloudflare Tunnel URL Changed
- **Symptoms**: WhatsApp messages receive no replies; Cloudflare terminal was restarted.
- **Cause**: Cloudflare Quick Tunnels generate ephemeral URLs that change on every restart.
- **Solution**:
  1. Copy the new `https://<subdomain>.trycloudflare.com` URL from the terminal.
  2. Update the Callback URL under **WhatsApp** $\rightarrow$ **Configuration** in the Meta Developer Console:  
     `https://<subdomain>.trycloudflare.com/api/v1/whatsapp/webhook`.
  3. Click **Verify and Save**.

---

## 2. Voice & Audio Processing Issues

### Issue 2.1: FFmpeg Binary Not Found
- **Symptoms**: Voice note processing fails with `FileNotFoundError: ffmpeg`.
- **Cause**: The system PATH does not include FFmpeg.
- **Solution**:
  - Aevora AI automatically resolves the bundled binary from `imageio-ffmpeg` (`.venv/Lib/site-packages/imageio_ffmpeg/binaries/`).
  - If missing, run:
    ```powershell
    .\.venv\Scripts\pip install imageio-ffmpeg
    ```
  - Or install globally via winget:
    ```powershell
    winget install Gyan.FFmpeg
    ```

### Issue 2.2: Slow Voice Note Transcription on CPU
- **Symptoms**: Audio transcription takes 8–15 seconds per message.
- **Cause**: Machine lacks an NVIDIA GPU or CUDA runtime, running Whisper on CPU with `int8` quantization.
- **Solution**:
  - This is expected behavior on standard CPUs. Aevora executes Whisper in a background thread pool (`asyncio.to_thread`) with a bounded semaphore so the FastAPI event loop never stalls.
  - To optimize, verify `WHISPER_MODEL_SIZE=base` or `tiny` in `.env`.

### Issue 2.3: Audio Download Fails with Untrusted Host Error
- **Symptoms**: Log records: `Untrusted or insecure media host: '...'`.
- **Cause**: The download URL does not belong to Meta's verified domain list (`lookaside.fbsbx.com`, `*.facebook.com`, `*.fbcdn.net`).
- **Solution**: This is a security feature preventing Server-Side Request Forgery (SSRF). Ensure the webhook payload originated directly from Meta's official Graph API.

---

## 3. Gemini & RAG Retrieval Issues

### Issue 3.1: Response Truncation or Incomplete Sentences
- **Symptoms**: Assistant replies cut off mid-sentence.
- **Cause**: Gemini 2.5 Flash default reasoning/thinking models consume output tokens from `max_output_tokens`.
- **Solution**: Aevora AI explicitly disables the thinking budget (`types.ThinkingConfig(thinking_budget=0)` in `app/ai/gemini_client.py`), reserving 100% of the token quota for the receptionist response.

### Issue 3.2: Retrieval Low Evidence Warnings
- **Symptoms**: Assistant replies: *"I could not find verified information on that in our clinic directory."*
- **Cause**: Query asked about unindexed doctors, treatments, or services outside NovaCare Medical Centre records.
- **Solution**: This is intended behavior. The hybrid RAG pipeline uses Reciprocal Rank Fusion and threshold filtering ($k=60$) to prevent fabricated clinic facts.

### Issue 3.3: Missing Vector Store Index
- **Symptoms**: Error on startup or chat: `FAISS index file not found`.
- **Solution**: Run the automated knowledge base build script:
  ```powershell
  .\scripts\build_knowledge_base.ps1
  ```

---

## 4. Staff Dashboard & Authentication Issues

### Issue 4.1: Dashboard Returns 401 Unauthorized
- **Symptoms**: Redirected to login modal or red alert: *"Session expired"*.
- **Cause**: JWT token expired (default 8 hours) or invalid credentials.
- **Solution**:
  - Sign in using the default credentials: `admin` / `NovaCare2026!`.
  - To reset the administrator password, update `STAFF_ADMIN_PASSWORD` in `.env` and delete `aevora.db` (in development only) or update the `StaffUser` record.

### Issue 4.2: Dashboard Shows Static Offline Badges
- **Symptoms**: Diagnostics card displays *Offline* for WhatsApp or Gemini.
- **Solution**: Check that `GEMINI_API_KEY` and `WHATSAPP_ENABLED=true` are configured in `.env`. When external credentials are blank, Aevora AI operates in offline mock mode to allow testing without cost.
