# 🎙️ Movement Voice Agent (Clairvoyant) | Enterprise Security Audit

> **🏆 Google DeepMind Gemini 3 - Marathon Agent Track**
> **Security Status:** Audited & Sanitized (v4.1.0)

This repository contains the source code for an Enterprise-grade AI Voice Agent designed for mortgage sales. It leverages **Google Gemini 3** for reasoning, **Vonage/Dialogflow CX** for telephony, and **Salesforce** for CRM integration.

## 🔐 Security Architecture

This system is built with a "Security First" methodology, adhering to strict compliance standards for Fintech applications.

### 1. Sanitization Protocol
- **No Hardcoded Secrets:** All API keys, passwords, and sensitive endpoints are managed via environment variables (`os.getenv`).
- **Input Validation:** All API endpoints utilize **Pydantic Models** for strict type checking and schema validation.
- **Type Safety:** The codebase enforces Python 3.10+ strict type hinting to prevent runtime type errors.

### 2. The "Audit Layer" (Reviewer Agent)
Located in `agents/reviewer.py`, the **Reviewer Agent** is a specialized, adversarial AI model that:
- Evaluates all AI-generated content against a strict rubric.
- Enforces **Falsifiability** and **Internal Consistency**.
- Acts as a "Human-in-the-Loop" proxy for compliance checks.
- Returns a cryptographic-style verdict (PASS/FAIL) before any action is taken.

### 3. Thought Signatures (Non-Repudiation)
Every AI decision generates a **Thought Signature**—a SHA-256 hash of the reasoning chain.
- **Traceability:** Every action (e.g., booking an appointment) is linked to a specific thought process.
- **Audit Log:** Signatures are stored in a tamper-evident log (`decision_audit_log`).

## 🧠 System Components

- **`app.py`**: The core FastAPI orchestrator. Handles webhooks, context management, and Gemini integration.
- **`salesforce_client.py`**: A robust, type-safe client for bi-directional Salesforce sync.
- **`campaign_manager.py`**: Manages outbound calling campaigns. Defaults to **Simulation Mode** for safe testing without telephony charges.
- **`agents/reviewer.py`**: The compliance engine.

## 🚀 Setup & Deployment

### Environment Configuration
Copy `sample.env` to `.env` and populate the required secrets:
```bash
cp sample.env .env
```

### Local Execution (Agile Development)
The system supports local execution for rapid prototyping:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app:app --reload
```

### Simulation Mode
By default, the `CampaignManager` runs in **Simulation Mode**. This generates realistic synthetic call data (Voicemail, Connected, Appointment) and logs it to the dashboard, allowing for end-to-end testing of the CRM integration without making real calls.

## ⚖️ Compliance & Guardrails
- **Mandatory Disclaimers:** Automated injection of recording consent.
- **No-Guarantee Enforcement:** AI prompts strictly forbid guaranteeing rates (enforces "could save", "may reduce").
- **Local Fallback:** Supports local LLM execution (Ollama) for data privacy compliance.

---
*Maintained by the Enterprise AI Architecture Team.*
