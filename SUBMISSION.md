# 🎙️ Movement Voice Agent — Gemini 3 Hackathon Submission

## Gemini 3 Integration (~200 words)

**Movement Voice Agent** is an autonomous outbound sales agent powered by **Gemini 3 Flash Preview** that operates across voice, SMS, and email channels without human supervision.

### Core Gemini 3 Features Used:

1. **ThinkingConfig with MINIMAL Level** — The agent uses Gemini 3's native thinking capabilities optimized for low-latency telephony. The `MINIMAL` thinking level enables fast decision-making during live calls while maintaining reasoning quality.

2. **Structured JSON Output Mode** — Using `response_mime_type="application/json"`, the agent produces structured action plans with explicit tool calls (`send_sms`, `send_email`, `schedule`, `browser_automation`) that execute autonomously.

3. **Multi-Step Tool Orchestration** — This is a **Marathon Agent**: a single conversation can span lead qualification, objection handling, appointment scheduling, SMS follow-up, and CRM updates—all orchestrated by Gemini 3's reasoning without returning to a human operator.

4. **SSML Voice Synthesis Integration** — Natural speech markers (`[pause]`, `[breath]`, `[thinking]`) are transformed into SSML prosody controls, creating human-like conversational flow.

### Why This Isn't a Simple Chatbot:
This system replaces an entire sales team workflow. Gemini 3 doesn't just respond—it **plans**, **executes**, and **adapts** across communication channels in real-time.

---

## 🔗 Links

| Resource | URL |
|----------|-----|
| **Live Demo** | https://movement-voice-agent-235894147478.us-central1.run.app |
| **Repository** | https://github.com/Phil-Hills/movement-voice-agent |
| **Demo Video** | *(To be recorded)* |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MOVEMENT VOICE AGENT                      │
├─────────────────────────────────────────────────────────────┤
│   Vonage/Dialogflow CX  ──►  FastAPI Webhook               │
│              │                                              │
│              ▼                                              │
│   ┌─────────────────────────────────────────┐              │
│   │     GEMINI 3 FLASH PREVIEW              │              │
│   │  ┌─────────────────────────────────┐    │              │
│   │  │ ThinkingConfig: MINIMAL         │    │              │
│   │  │ Output: JSON Action Plan        │    │              │
│   │  └─────────────────────────────────┘    │              │
│   └─────────────────────────────────────────┘              │
│              │                                              │
│              ▼                                              │
│   ┌─────────────────────────────────────────┐              │
│   │  AUTONOMOUS TOOL EXECUTION              │              │
│   │  • send_sms    • send_email             │              │
│   │  • schedule    • browser_automation     │              │
│   │  • update_crm  • log_disposition        │              │
│   └─────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Strategic Track: Marathon Agent

This project demonstrates the **Action Era** vision:
- **Autonomous multi-step execution** across hours/days
- **Self-correcting tool calls** without human supervision
- **Real-world business impact** — replaces outbound sales workflows

---

## 📹 Demo Video Script (3 min max)

1. **0:00-0:30** — Introduction: "This is Jason, an autonomous AI sales agent..."
2. **0:30-1:30** — Live call demo showing Gemini 3 reasoning + SSML voice
3. **1:30-2:15** — Show multi-channel action execution (SMS sent, calendar booked)
4. **2:15-3:00** — Architecture walkthrough + ThinkingConfig explanation

---

*Built by Phil Hills | Seattle, 2026*
