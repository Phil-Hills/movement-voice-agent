# Codebase Summary: Movement Voice Agent (Clairvoyant)

This repository contains the source code for **Clairvoyant**, an AI-powered voice agent for sales and mortgage applications. The system leverages **FastAPI** for the backend, **Google Cloud (Vertex AI/Gemini)** for intelligence, **ElevenLabs** for voice synthesis, and **Salesforce** for CRM integration. It is designed to autonomously handle outbound calls, qualify leads, and schedule appointments.

## 1. Project Overview
-   **Goal**: Create an autonomous AI sales agent ("Jason") that can conduct natural conversations, research companies, and integrate with enterprise systems.
-   **Key Technologies**: Python, FastAPI, Google Gemini (Flash/Pro), ElevenLabs, Salesforce API, Vonage (telephony), Playwright (browser automation).
-   **Architecture**:
    -   **Backend**: `app.py` (FastAPI) serves as the central orchestrator.
    -   **Intelligence**: `agent.py` and `app.py` handle LLM interactions (Gemini).
    -   **CRM**: `salesforce_client.py` manages bi-directional data sync with Salesforce.
    -   **Telephony**: `call_clients.py` and `campaign_manager.py` handle outbound calling logic.
    -   **Frontend**: HTML templates (`dashboard.html`, `index.html`) provide a UI for monitoring and control.

## 2. Key Components & File Analysis

### Core Application
-   **`app.py`**: The main entry point.
    -   Initializes the FastAPI app, logging, and environment variables.
    -   Configures **Gemini models** (Thinking/Flash) and **ElevenLabs** for TTS.
    -   Implements **Thought Signatures** (`generate_thought_signature`, `log_decision`) to audit AI reasoning.
    -   Manages **Lead State** (Firestore or in-memory) and **Q-Memory** (knowledge base to prevent redundant work).
    -   Exposes API endpoints for:
        -   Chat (`/demo`)
        -   Lead Management (`/api/leads`)
        -   Campaign Control (`/api/campaigns`)
        -   Salesforce OAuth (`/oauth`)
        -   Dashboard Stats (`/api/dashboard`)

-   **`agent.py`**:
    -   Contains a basic `MovementAgent` class with a system prompt. It appears to be a lightweight wrapper or placeholder, as much of the logic resides in `app.py`.

-   **`agent_interface.py`**:
    -   Defines the **Q Protocol** interface (`BaseAgent`, `TaskRequest`, `TaskResponse`).
    -   Standardizes how agents communicate and log work (Receipts).
    -   Used by the `Clairvoyant` agent in `app.py`.

### Integrations
-   **`salesforce_client.py`**:
    -   A robust client for Salesforce interaction using `simple_salesforce`.
    -   Handles authentication (OAuth/Password).
    -   Provides methods to:
        -   Fetch leads (`get_lead`, `get_leads_for_campaign`).
        -   Update dispositions (`update_lead_disposition`).
        -   Log calls and create tasks (`log_call`, `create_task`).
    -   Includes a **Demo Mode** with mock data if credentials are missing.

-   **`campaign_manager.py`**:
    -   Manages the execution of outbound calling campaigns.
    -   Loads leads from CSV or Salesforce.
    -   Simulates a **Power Dialer**:
        -   Iterates through leads.
        -   Simulates call outcomes (Connected, Voicemail, Appointment).
        -   Logs results back to Salesforce (or demo log).
    -   Runs asynchronously using `asyncio`.

-   **`call_clients.py`**:
    -   A script for triggering real outbound calls using **Vonage**.
    -   Connects calls to a Dialogflow agent.
    -   Parses a `clients.csv` file for target numbers.

-   **`browser_agent.py`**:
    -   Uses **Playwright** to automate web browser tasks.
    -   Includes a function `submit_movement_application` to fill out loan applications on a website (mocked logic).

-   **`verify_salesforce.py`**:
    -   A utility script to test the Salesforce connection and print user info.

-   **`agents/reviewer.py`**:
    -   Implements a "Strict Reviewer Agent" using an LLM.
    -   Evaluates submissions based on a strict rubric (Consistency, Falsifiability).
    -   Outputs a JSON verdict (PASS/FAIL).

### Frontend
-   **`templates/dashboard.html`**:
    -   A comprehensive admin dashboard.
    -   Visualizes stats (Calls Made, Appointments).
    -   Provides controls for uploading campaigns (CSV/Salesforce) and starting the Power Dialer.
    -   Displays a live feed of call activity.
-   **`templates/index.html`**:
    -   The public-facing landing page / demo interface.
    -   Features a "Voice Clone" chat interface.
    -   Allows users to interact with "Clairvoyant" (text/voice).
    -   Visualizes the "Thinking Level" and AI processing.

## 3. Data Flow
1.  **Lead Ingestion**: Leads are loaded via CSV upload (`/api/leads/upload`) or Salesforce sync (`/api/campaigns/import-salesforce`).
2.  **Campaign Execution**: The `CampaignManager` iterates through the lead list.
3.  **Interaction**:
    -   **Simulation**: In demo mode, `campaign_manager.py` simulates call outcomes.
    -   **Real Call**: `call_clients.py` triggers Vonage to dial the user and connect to the AI.
    -   **Web Chat**: Users interact via `index.html`, hitting the `/demo` endpoint in `app.py`.
4.  **Intelligence**: `app.py` sends user input to Gemini.
    -   It may perform **Company Research** (Google Search Grounding).
    -   It generates a response and a **Thought Signature**.
5.  **Action**:
    -   **TTS**: The response is converted to audio via ElevenLabs.
    -   **CRM Update**: The interaction is logged in Salesforce (Task/Lead status).

## 4. Current Status
-   **Functional**: The core FastAPI server, Dashboard UI, and Simulation logic are implemented.
-   **Demo Ready**: The system gracefully degrades to "Demo Mode" if external API keys (Salesforce, Vonage) are missing, using mock data.
-   **AI Integration**: Gemini integration is set up with "Thinking Levels" (High/Medium/Low) to adjust reasoning depth.
-   **Q Protocol**: The system implements a structured "Receipt" system for auditing AI actions.

This summary captures the essence of the codebase as of the latest commit.
