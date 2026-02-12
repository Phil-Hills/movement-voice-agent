# Technical Deep-Dive: Dual-Core Intelligence

The Core Voice Agent (Jason) operates on a **Dual-Core Intelligence** model. This architecture differentiates it from standard "wrapper" bots by separating *deterministic knowledge* from *probabilistic reasoning*.

---

## 1. Structured Core (The Memory)
The agent is grounded through the **Q Protocol**, which provides a "Structured Core" of truth.

- **Canonical Narrative**: A living document (`canonical_narrative.md`) that defines the agent's world-view, architecture, and mission. This is injected into every conversation turn.
- **CRM Persistence**: Direct sync with Salesforce ensures the agent "remembers" the lead's status, previous touches, and specific NMLS compliance requirements.
- **Data Sovereignty**: By using structured memories, we ensure Jason doesn't guess names or company details; he polls the **A2AC Research Agent** to retrieve verified facts.

## 2. Thinking Core (The Reasoner)
Jason utilizes **Gemini 2.0 Flash Thinking** to perform "Asymmetric Reasoning" before speaking.

- **The Reasoner-Talker Loop**: 
  - **The Reasoner**: Performs a hidden planning step. It checks the *Structured Core*, triggers compliance guardrails (e.g., "Am I about to quote a rate?"), and hashes its plan into a `thought_signature`.
  - **The Talker**: Converts the validated plan into a concise, warm voice output.
- **Cryptographic Grounding**: Every "thought" is signed with a SHA256 hash. If the agent's reasoning deviates from the structured memory, the signature changes, providing an auditable trail.

## 3. The Result: Zero-Hallucination Conversations
By combining **Structured Memories** (the *what*) with **Native Thinking** (the *how*), Jason achieves:
- **Sub-500ms Response Times**: Fast enough for natural voice.
- **Deterministic Compliance**: He "thinks" about the rules (TRID, Reg Z) before he speaks.
- **Self-Correction**: If the user pushes for a rate, Jason's reasoning step detects the violation and triggers a mandatory handoff.

---
*Architectural Blueprint | Phil Hills AI Lab | Feb 2026*
