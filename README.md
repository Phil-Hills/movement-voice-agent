# 🎙️ Voice Agent: A Smarter Way to Connect with Borrowers [v6.0.0]

> **Category:** Digital Innovation | **Read time:** 3 min | **Maintainer:** AI Lab

The **Voice Agent Agent** (Jason) is designed to improve borrower conversations and help you stay better connected throughout the loan journey. By introducing AI-driven orchestration, Jason handles the administrative heavy lifting so you can focus on building relationships.

---

## 📽️ Experience the Swarm
Experience the future of mortgage orchestration today through our high-fidelity simulation suite.

👉 **[View Agentic Swarm Orchestration](./docs/strategy/SWARM_ORCHESTRATION_AND_LIFECYCLE.md)**
👉 **[Phase 1 Install Guide: Step-by-Step Onboarding](./docs/ops/INSTALL_GUIDE.md)**

---

## 🚀 New Features in v6.0.0



### 🎯 Campaign & Cadence Engine
Automatically creates marketing campaigns from refi-ready borrowers and runs multi-channel outreach cadences.

| Day | Channel | Action |
| :--- | :--- | :--- |
| 0 | 📧 **Email** | Personalized rate drop notification with savings calculation |
| 1 | 💬 **SMS Magic** | Short follow-up text with savings highlight |
| 3 | 📞 **Vonage Voice** | AI-initiated courtesy call with IVR press-to-connect |
| 5 | 💬 **SMS Magic** | Second text touchpoint with rate quote offer |
| 7 | 📧 **Email** | Full personalized rate analysis breakdown |
| 10 | 📞 **Voice** | Final check-in call with direct connection |

**API Endpoints:**
- `POST /api/campaigns/create-from-pipeline` — Auto-create from refi-ready list
- `POST /api/campaigns/{id}/execute-step` — Advance cadence for all leads
- `GET /api/campaigns/{id}/status` — View lead progress and response tracking

### ⏰ Daily Automation (Cloud Scheduler)
A GCP Cloud Scheduler job fires every morning at **7:00 AM PT** and automatically:
1. Analyzes the pipeline against current market rates
2. Sends a formatted email briefing with refi opportunities
3. Auto-creates campaigns from newly eligible borrowers
4. Advances active campaign cadences to the next touchpoint

---

## ✅ Previous Features
- **Hyper-Channel Orchestration**: Jason can follow up via SMS, Email, and Physical Mail
- **The Licensing Duty Gate**: Built-in compliance that auto-hands-off rate conversations to the LO
- **Real-Time Pipeline Debriefs**: Start your day with a clear summary of Jason's overnight calls

---

## 🗺️ The "Move More" Resource Map

| **Resource** | **Location** | **Benefit** |
| :--- | :--- | :--- |

| **🧠 Intelligence** | [Core Engine](./core/agent_engine.py) | High-thinking qualification that sounds human |
| **📑 Compliance** | [Safety Gate](./docs/compliance/LICENSED_DUTY_GUARDRAILS.md) | 100% compliant with NMLS duty guardrails |
| **🔭 Strategy** | [Workflow 2026](./docs/strategy/ORIGINATOR_WORKFLOW_2026.md) | How Jason handles the 'Marathon' doc chase |
| **⚡ Operations** | [Admin Guide](./docs/ops/SF_ADMIN_GUIDE.md) | Easy setup for your Salesforce environment |
| **💰 Economics** | [Unit ROI](./docs/strategy/COST_ECONOMICS.md) | Massive savings vs. traditional cold-calling |
| **🔭 MORE Sync** | [SF MORE Strategy](./docs/strategy/SALESFORCE_MORE_STRATEGY.md) | Deep integration with Movement's MORE platform |

---

### Deployment & Configuration

All channels operate in **dry-run mode** until API keys are configured — no accidental sends.

---

## ⚖️ Staying Compliant
Trust is everything. Jason is engineered to protect your license and your reputation.

*   **Mandatory Handoff**: When a borrower asks "What's my rate?", Jason immediately connects them to you.
*   **Cryptographic Audit**: Every conversation is planed and signed with a `thought_signature`.
*   **TCPA scrubbing**: Automated Do Not Call checks are baked into every campaign.

---

## 📈 The Result: Move More with Cognitive Luxury
By delegating document chasing, partner recruitment, and initial qualification to Jason, you reclaim your most valuable asset: **Your Attention.**

👉 [Explore the Full Swarm Orchestration Strategy](./docs/strategy/SWARM_ORCHESTRATION_AND_LIFECYCLE.md)

---
**Questions?**
Check out our weekly office hours or visit the MORE Marketplace to see these features in action.

*Company Mortgage Powered by AI Lab ™ Version 6.0.0*

