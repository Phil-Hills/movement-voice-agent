# Project Context: Movement Voice Agent

## 📍 Location
- **Directory**: `c:\Users\bphil\movement-voice-agent`
- **Type**: Python / FastAPI Backend

## 🎯 Project Goals
1.  **AI Sales Agent**: Provide a voice-enabled, autonomous sales agent ("Clairvoyant").
2.  **Salesforce Integration**: Bi-directional sync with Salesforce Leads and Activities.
3.  **Hachathon Features**:
    -   **Gemini 3 Integration**: "Thinking" models for complex reasoning.
    -   **Google Search Grounding**: Real-time company research.
    -   **No Redundant Work**: Q Protocol integration to use local Brain memory before external API calls.

## 🏗️ Architecture
-   **Entry Point**: `app.py` (FastAPI)
-   **Knowledge Base**: `../ai-summary-cube/brain/cubes/core_knowledge` (QMem Binary)
-   **Frontend**: `templates/` (Jinja2 Dashboard)

## 🚀 Current Status
-   Running on `http://localhost:8000`
-   Q Protocol Memory Loaded: 21 atoms
-   Salesforce OAuth: Configured
