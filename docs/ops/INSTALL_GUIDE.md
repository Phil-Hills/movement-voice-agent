# Installation Guide: Deploying Movement Voice [Jason]

> **Category:** Operations | **Read time:** 10 min | **Maintainer:** Phil Hills AI Lab

This guide provides a professional, step-by-step process for deploying the **Movement Voice** platform within your environment.

---

## 🛠️ 1. Prerequisites
Before beginning the installation, ensure you have the following accounts and credentials prepared:

| **Platform** | **Requirement** |
| :--- | :--- |
| **Python** | Version 3.10+ installed locally. |
| **GCP** | Project ID with Billing enabled (for Cloud Run). |
| **Salesforce** | Admin access to a Developer Org or Sandbox (MORE platform). |
| **Vonage** | API Key and Secret for Voice/SMS orchestration. |
| **Google AI** | API Key for Gemini 2.0 Flash Thinking. |

---

## 🏗️ 2. Local Environment Setup
Follow these steps to prepare your local development workspace:

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Phil-Hills/movement-voice-agent.git
    cd movement-voice-agent
    ```

2.  **Initialize Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Environment Variables**:
    Create a `.env` file in the root directory and populate with your credentials:
    ```env
    GOOGLE_API_KEY=your_gemini_key
    SALESFORCE_USERNAME=your_sf_admin_user
    SALESFORCE_PASSWORD=your_sf_password
    SALESFORCE_SECURITY_TOKEN=your_sf_token
    VONAGE_API_KEY=your_vonage_key
    VONAGE_API_SECRET=your_vonage_secret
    VONAGE_APPLICATION_ID=your_vonage_app_id
    ```

---

## ☁️ 3. GCP Deployment
The platform is optimized for **Google Cloud Run** for high-scale, pay-per-request performance.

1.  **Grant Permissions**:
    Ensure your local `gcloud` CLI is authenticated and the project is set.
2.  **Deploy the Swarm**:
    ```bash
    bash scripts/deploy_gcp.sh
    ```
3.  **Secure Your Secrets**:
    Store sensitive keys in GCP Secret Manager as per the [Infrastructure Guide](file:///Users/SoundComputer/Downloads/a2ac.ai/movement-voice-agent/docs/ops/INFRASTRUCTURE_GUIDE.md).

---

## 🌉 4. Salesforce MORE Integration
To connect Jason to your Salesforce environment:

1.  **Create Connected App**: In Salesforce, create a new Connected App with OAuth scopes for Lead, Task, and API access.
2.  **Map Field IDs**: Ensure your Lead fields (e.g., `Loan_Program__c`, `DNC_Flag__c`) match the schema in [lead_management.py](file:///Users/SoundComputer/Downloads/a2ac.ai/movement-voice-agent/core/lead_management.py).
3.  **Verify Webhooks**: Configure your Vonage Application to point its Answer/Event URLs to your Cloud Run endpoint suffix `/vonage/answer`.

---

## ✅ 5. Verification Ritual
To ensure the system is correctly grounded and operational:

1.  **Run Security Audit**:
    ```bash
    python3 scripts/enterprise_audit_op.py
    ```
2.  **Verify Hashing**:
    Confirm the BLAKE3 signatures are generating in the logs:
    ```bash
    # Look for "tsig_..." markers in your terminal
    ```
3.  **Test "Move More" Flow**:
    Trigger a mock lead through Salesforce and verify the outbound call or SMS is queued.

---
*Movement Mortgage Powered by Phil Hills AI Lab ™*
*Proprietary Sovereign Strategy*
