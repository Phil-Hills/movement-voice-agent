# Phase 2: AI Voice System Implementation

## Goal
Build a deployable AI Sales Agent that can handle inbound/outbound calls using Google Cloud.

## Architecture
- **Core**: FastAPI application running on Cloud Run.
- **Brain**: Vertex AI (Gemini Flash) for fast, natural conversation.
- **Voice**: Google Cloud TTS (Neural2) + Speech-to-Text.
- **Telephony**: Google Cloud Voice (or Twilio SIP if preferred).

## Implementation Steps

### 1. The "Brain" Server (`voice_system/app.py`)
- FastAPI endpoints to handle call events (start, media, dtmf, end).
- WebSocket or HTTP stream for real-time audio handling.
- State management for conversation context.

### 2. The Agent Logic (`voice_system/agent.py`)
- Defines the "Sales Persona" (likely using the Jason/Voice Architect personas).
- Handles NLU (Intent detection) and NLG (Response generation).
- Interruption handling logic (if using streaming).

### 3. Deployment (`voice_system/Dockerfile`)
- Containerize the application.
- Deploy to the existing `deployment-2026-core` project.

## Selected Architecture: Google Native (Dialogflow CX)
We will use **Dialogflow CX Phone Gateway** as the "Body" (handling Telephony/ASR/TTS) and Cloud Run as the "Brain" (Webhook).

### Data Flow
1. **User calls Google Number**: Dialogflow CX answers.
2. **ASR (Google)**: Transcribes speech to text.
3. **Webhook (Cloud Run)**: 
   - Dialogflow sends POST to `/webhook`.
   - Payload contains User Text.
   - **Brain** (Gemini) processes text.
   - Response contains Agent Text.
4. **TTS (Google)**: Dialogflow speaks the response to the user.

### Advantages
- **Billing**: 100% on GCP Bill.
- **Simplicity**: No WebSockets or raw audio handling.
- **Reliability**: Google manages the telephony stack.

## Environment Variables Required
- `GOOGLE_CLOUD_PROJECT`
- (No external API keys needed!)


## Phase 3: Universal Flow & Structured Intelligence
**Goal**: Transition from simple text generation to a structured decision engine that drives a "Universal Call Flow" for Brad Overlin.
- [x] **Universal Script**: Implement the branching logic (VA/Conv/Jumbo) in a single system prompt.
- [x] **Structured Intelligence**: Update Brain to output JSON (`text`, `score`, `disposition`) instead of raw text.
- [x] **Lead Scoring**: Implement scoring rules (+15 for Goal, +30 for Appt) within the Brain's logic.
- [x] **Webhook Upgrade**: Map Brain's JSON output to Dialogflow `sessionInfo.parameters` for real-time tracking.

## Verification Plan
- Deploy to Cloud Run.
- Connect phone number to Cloud Run URL.
- Call the number and talk to the agent.
