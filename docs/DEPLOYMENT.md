# Aevora AI — Deployment & Infrastructure Guide

This guide details local Windows deployment, Cloudflare Quick Tunnel configuration for Meta WhatsApp webhooks, and an engineering evaluation of free cloud hosting options.

---

## 1. Primary Deployment: Local Windows Workstation

The primary target is a standard Windows 10/11 development machine. This satisfies all project requirements without introducing paid cloud infrastructure (AWS, Azure, Pinecone, or Redis).

### Architecture Components
- **ASGI Server**: Uvicorn running FastAPI on `127.0.0.1:8000`.
- **Database**: Embedded SQLite database (`aevora.db`) with WAL mode.
- **Vector Store**: Local FAISS CPU index (`data/vector_store/faiss_index.bin`) and BM25 JSON corpus.
- **Speech Models**: Local Faster-Whisper model cached on disk with bundled FFmpeg (`imageio-ffmpeg`).
- **Webhook Bridge**: Cloudflare Quick Tunnel (`cloudflared`) exposing local port 8000 to public HTTPS for Meta WhatsApp webhooks.

### Quickstart Execution

```powershell
# Step 1: Automated provisioning
.\scripts\setup_windows.ps1

# Step 2: Build or rebuild knowledge base index
.\scripts\build_knowledge_base.ps1

# Step 3: Run automated verification tests
.\scripts\run_tests.ps1

# Step 4: Start application server
.\scripts\start_windows.ps1
```

Once started:
- **Staff Dashboard**: `http://127.0.0.1:8000/dashboard`
- **API Documentation**: `http://127.0.0.1:8000/docs`
- **Health Check**: `http://127.0.0.1:8000/health`

---

## 2. Exposing Webhooks via Cloudflare Quick Tunnel

Meta WhatsApp Cloud API requires a publicly reachable, trusted HTTPS URL. Cloudflare Quick Tunnel provides this at zero cost without port forwarding or account registration.

### 1. Download `cloudflared`
- Download Windows x64 binary from [Cloudflare Tunnel GitHub Releases](https://github.com/cloudflare/cloudflared/releases) or via winget:
  ```powershell
  winget install --id Cloudflare.cloudflared
  ```

### 2. Start the Tunnel
In a dedicated PowerShell terminal:
```powershell
cloudflared tunnel --url http://localhost:8000
```

Cloudflare outputs an ephemeral HTTPS domain:
```text
https://random-assigned-subdomain.trycloudflare.com
```

### 3. Configure in Meta Developer Console
- **Webhook URL**: `https://random-assigned-subdomain.trycloudflare.com/api/v1/whatsapp/webhook`
- **Verify Token**: Must match `WEBHOOK_VERIFY_TOKEN` in `.env` (e.g. `aevora_clinic_verify_tok_2026`).
- **Subscribed Fields**: `messages`.

### 4. Important Operational Notes
- **Temporary URL**: Quick tunnel URLs change whenever the tunnel process is restarted. When restarting, update the Callback URL in the Meta Developer Console.
- **Host Availability**: The local workstation and application must remain powered on and running during active demonstrations.
- **Demonstration Scope**: This single-instance arrangement is designed for hiring assessments and technical demonstrations rather than multi-tenant horizontal production clusters.

---

## 3. Free Cloud Hosting Options: Technical Feasibility Audit

We evaluated multiple free-tier cloud platforms against Aevora AI's technical footprint:

| Platform | Free Tier Specifications | Feasibility for Aevora AI | Analysis & Decision |
| :--- | :--- | :---: | :--- |
| **Render** | 512 MB RAM, spins down after 15m idle | **Infeasible** | Faster-Whisper + PyTorch + SentenceTransformers requires ~1.5 GB memory. 512 MB results in Out-Of-Memory (OOM) process termination during startup. Cold start (50s) violates Meta webhook timeout ($\le 5$s). |
| **Koyeb** | 512 MB RAM, nano instance | **Infeasible** | Memory limit too low for local FAISS vector search and speech models simultaneously. |
| **Hugging Face Spaces** | 16 GB RAM, 2 vCPU | **Partial** | Excellent memory for AI models; however, external webhook ingress is blocked or throttled by anti-bot proxies, making Meta webhook verification unreliable. |
| **Railway** | \$5 trial credit, then paid | **Disqualified** | Violates zero-cost constraint. |
| **Local Machine + Cloudflare** | **Full PC resources (CPU/GPU, RAM)** | **Recommended** | **100% reliable, zero cost, no memory bounds, zero cold-start delay, immediate webhook processing.** |

**Conclusion**: Local workstation hosting with Cloudflare Quick Tunnel is the most reliable, honest, and performant zero-cost deployment architecture for this demonstration product.
