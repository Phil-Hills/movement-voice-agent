# 🎙️ Movement Voice Agent (Jason)

Enterprise-grade AI Voice Agent for **Brad Overlin @ Movement Mortgage**. This agent is designed to handle outbound and inbound telephony via **Dialogflow CX**, powered by **Gemini 1.5 Flash**.

## 🧠 System Architecture
- **NLP/LLM:** Google Gemini 1.5 Flash (Vertex AI)
- **Integration:** Dialogflow CX Telephony
- **Orchestration:** Python FastAPI Webhook
- **Persona:** "Jason" - Friendly, professional, and compliant mortgage specialist.

## 📁 Repository Structure
- `agent.py`: Core brain using Vertex AI with the "Movement Mortgage" systemic prompt and lead scoring logic.
- `app.py`: FastAPI webhook server compliant with Dialogflow CX protocol.
- `agent_config.blob`: Exported Dialogflow CX agent configuration (Intents, Flows, Pages).
- `Dockerfile`: Containerization for Cloud Run deployment.
- `implementation_plan.md`: Roadmap and design notes.

## 🚀 Deployment Status
- **Project:** `deployment-2026-core`
- **Region:** `us-central1`
- **Service:** `voice-sales-agent`
- **Webhook URL:** `https://voice-sales-agent-5zkzqcunjq-uc.a.run.app/webhook`

## ⚖️ Compliance & Guardrails
- Automatic lead scoring (VA/Conv/Jumbo).
- Mandatory recording disclaimer in opening.
- No-guarantee language enforcement ("could save", "may reduce").
- Direct booking link to Brad Overlin's calendar.

---
*Maintained by Phil Hills AI Lab.*
