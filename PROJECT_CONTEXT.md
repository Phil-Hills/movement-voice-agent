# Project Context: Movement Voice Agent

## 📍 Location
- **Directory**: `c:\Users\bphil\movement-voice-agent`
- **Type**: Python / FastAPI Backend

## 🎯 Project Goals
1.  **AI Voice Agent (Jason)**: High-fidelity mortgage specialist with VA/Conv/Jumbo logic.
2.  **Salesforce Integration**: Hardened bi-directional sync (11-touch cadence).
3.  **Modular Logic**: Separation of AgentEngine, LeadManager, and ResearchEngine for production stability.

## 🏗️ Architecture
-   **Entry Point**: `app.py` (FastAPI)
-   **Core Module**: `/core` (Agent, Lead, Research logic)
-   **Knowledge Base**: Q-Memory (A2AC Protocol)
-   **Frontend**: `templates/` (Premium Dashboard)
-   **Monitor**: `scripts/monitor.sh` (Brutalist CLI)
