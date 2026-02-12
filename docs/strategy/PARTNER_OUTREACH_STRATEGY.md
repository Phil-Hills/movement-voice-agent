# Strategic Protocol: Professional Partner Outreach (B2B)

This protocol outlines the transition of the Core Voice Agent from a B2C Lead Qualifier to a **B2B Partner Recruiter**. By targeting Real Estate Brokers as strategic partners, we demonstrate the platform's value while operating in a lower-friction regulatory environment.

## 🎯 Global Objective
Recruit high-volume Real Estate Brokers by pitching the **"AI-Enhanced Closing Experience"** as a competitive advantage for their agency.

## 🧠 Partner-Centric Persona: "Jason - Branch Relations"
The AI persona shifts from "helping with a loan" to "branch-level recruitment."

### Updated Key Directives:
- **The Hook**: "I'm calling on behalf of the local Mortgage Branch Manager. We’ve just launched a new series of specialized loan programs (VA, Jumbo, non-QM) and wanted to see if your agents could benefit from these in this market."
- **Value Prop**: Pitch 'New Programs' and 'Priority Support' as the primary wedge.
- **Goal**: Schedule a "Strategy Session" between the Real Estate Agent/Broker and the Branch Manager.

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
