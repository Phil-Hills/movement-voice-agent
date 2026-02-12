# Swarm Orchestration & Full Lifecycle Assistance

This guide defines the **Agentic Swarm** operational model and how the Core Voice Agent (Jason) supports the entire mortgage loan lifecycle, from initial pre-lead engagement to post-close retention.

---

## 🐝 The Agentic Swarm (A2AC Orchestration)
Jason does not operate in isolation. He is the "Voice Node" of a larger **A2AC (Agent-to-Agent Communication)** swarm.

- **Swarm Management**: Managed via a decentralized registry. Each agent (Research, Salesforce, Document, Voice) communicates via structured JSON payloads, delegating tasks that fall outside their specific domain.
- **Service Mesh**: Using the **Q Protocol**, agents can spin up specialized sub-agents (e.g., a "Tax Transcript Analyzer") to handle ephemeral processing tasks without human intervention.

## 📡 The Hyper-Channel Persistence Model
Jason operates across four distinct touch-points to ensure 100% lead saturation:

1. **Voice (Primary)**: High-thinking phone calls for qualification and partnership.
2. **SMS/Text**: Automated confirmations and "on-my-way" messages via Vonage SMS.
3. **Email**: Delivery of program brochures, meeting invites, and data-heavy briefs.
4. **Physical Mail**: High-value "Impact Mailers" (Thank you cards, program flyers) sent via Lob for premium partner nurturing.

---

## 🤝 Human-in-the-Loop (HITL) Protocols
The platform is designed as a **Co-Pilot**, not a replacement.

- **Strategic Handoffs**: When Jason detects complexity (e.g., specific rate negotiations or complex income structures), he triggers a Salesforce Task for the human NMLS Originator.
- **Supervised Learning**: Every **Thought Signature** and **Thinking Trace** is available for human review via the `monitor.sh` CLI. 
- **Approval Gates**: Critical actions (like final loan submission or official rate locks) require a human digital signature to execute.

---

## 📈 The Full Lifecycle: Pre-Lead to Post-Close

Jason assists the human NMLS Originator at every stage:

### 1. Pre-Lead & Discovery
- **Outbound Qualification**: Proactive calls to professional partners (Real Estate Brokers) to pitch new programs.
- **Top-of-Funnel Filtering**: Initial high-fidelity screening of cold leads to identify high-intent borrows.

### 2. In-Process & Document Collection
- **Automated Document Chasing**: Jason can call borrowers to request missing W2s, bank statements, or signatures.
- **Processing Tasks**: Utilizing the **Document Agent**, Jason can verify if a received document meets the underwriting criteria (e.g., "Is this bank statement from the last 30 days?").
- **Status Updates**: Automated "Marathon Agent" touchpoints to keep the borrower and realtor informed of the loan's progress.

### 3. Closing & Post-Close
- **Closing Coordination**: Confirming closing dates and times with title/escrow.
- **Post-Close Retention**: 6-month and 1-year follow-up calls to discuss recapture (refinance) opportunities during rate drops.
- **Referral Generation**: Engaging satisfied borrowers to secure professional referrals for the branch.

---
*Blueprint by Phil Hills AI Lab | Feb 2026*
