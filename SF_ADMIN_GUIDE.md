# Salesforce Admin Guide: Core Voice Agent Implementation

Follow these instructions to configure your Salesforce environment for the **Core Voice Agent** integration.

## 1. Connected App Setup [Security]
To enable OAuth communication between the Agent and Salesforce:
1. Navigate to **Setup** > **App Manager** > **New Connected App**.
2. **Name**: `CoreVoiceAgent_Integration`
3. **Scopes Required**:
    - `api` (Manage user data via APIs)
    - `refresh_token` (Perform requests at any time)
    - `web` (Provide access to custom web applications)
4. **IP Relaxation**: Ensure 'Enforce IP restrictions' is set correctly for your deployment environment.

## 2. Permission Set: "AI Agent Orchestrator"
Create a new Permission Set with the following access levels:
- **Lead Object**: Read, Edit, Create.
- **Task Object**: Read, Edit, Create.
- **Campaign Object**: Read-only.
- **Custom Fields** (Recommended):
    - `Current_Cadence_Step__c` (Number)
    - `Last_AI_Interaction__c` (DateTime)
    - `AI_Thought_Signature__c` (Long Text Area)

## 3. Compliance & Governance
- **Audit Logs**: The agent logs every reasoning step as a `Task`. Review these for quality assurance.
- **Data Sovereignty**: The agent only retrieves data for leads in active campaigns. No bulk sync of your entire database occurs.
- **DNC Enforcement**: The agent checks the `DoNotCall` flag on Lead/Contact records before initiating any Vonage call.

## 4. Vonage Integration
Ensure the **Vonage for Salesforce** package is installed and configured with the same API credentials used in the `.env` file of this application.

---
*Generated for Phil Hills AI Lab | Feb 2026*
