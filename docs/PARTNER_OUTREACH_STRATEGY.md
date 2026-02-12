# Strategic Protocol: Professional Partner Outreach (B2B)

This protocol outlines the transition of the Core Voice Agent from a B2C Lead Qualifier to a **B2B Partner Recruiter**. By targeting Real Estate Brokers as strategic partners, we demonstrate the platform's value while operating in a lower-friction regulatory environment.

## 🎯 Global Objective
Recruit high-volume Real Estate Brokers by pitching the **"AI-Enhanced Closing Experience"** as a competitive advantage for their agency.

## 🧠 Partner-Centric Persona: "Jason - Strategic Relations"
The AI persona shifts from "helping with a loan" to "optimizing a partnership."

### Updated Key Directives:
- **The Hook**: "I'm calling from the Phil Hills AI Lab on behalf of [Originator Name]. We’ve developed a technical wedge that helps brokers close 20% faster and wanted to sync on a partnership."
- **Value Prop**: Pitch the Core Voice Agent as a *shared resource* that the broker's clients can use for 24/7 instant qualification.
- **Goal**: Schedule a "Strategic Synergy" meeting (intro call or coffee) between the Broker and the NMLS Originator.

## ⚖️ Compliance & Safety Advantages
- **No Rate Quoting**: Outreach focuses on process, technology, and partnership terms—not loan specifics.
- **TCPA Compliance**: Still requires DNC scrubbing, but business-to-business (B2B) outreach typically has higher tolerance than residential cold-calling.
- **Regulatory Buffer**: Demonstrates the "Reasoner-Talker" loop in a professional negotiation context before wide-scale consumer deployment.

## 🛠️ Implementation Workflow
1. **Targeting**: Load Broker lists into [data/partners.csv](file:///Users/SoundComputer/Downloads/a2ac.ai/movement-voice-agent/data/partners.csv).
2. **Research**: `ResearchEngine` analyzes the broker's recent listings or agency specializations.
3. **Execution**: Outbound call via `CampaignManager` using the `PartnerRelations` prompt variant.
4. **Handoff**: Successful interest triggers a "High Priority Partnership Opportunity" task in Salesforce.

---
*Blueprint by Phil Hills AI Lab | Feb 2026*
