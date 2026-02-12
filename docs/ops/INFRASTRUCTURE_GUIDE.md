# Infrastructure Guide: Beta-to-Main Rollout Strategy

This guide outlines the protocol for scaling the Movement Voice Agent platform from a sandboxed **Beta** branch to a fully orchestrated multi-branch infrastructure.

## 🏗️ The Multi-Branch Architecture
We utilize a **Branch-per-Environment** model to ensure absolute semantic isolation of data and compute resources.

| Branch | Environment | Goal | Database | Vonage App |
| :--- | :--- | :--- | :--- | :--- |
| `beta` | Sandbox | Rapid experimentation & LLM fine-tuning. | Firestore (Test) | Sandbox App |
| `staging` | Pre-Prod | NMLS Compliance validation & UAT. | Read-only SF Sync | Staging App |
| `main` | Production | High-fidelity lead orchestration. | Live Salesforce App | Production App |

---

## 🚀 Phase 1: Starting with `beta`
The `beta` branch is your clinical trial environment.

1. **Branch Creation**:
   ```bash
   git checkout -b beta
   git push -u origin beta
   ```
2. **Environment Isolation**:
   - Create a specific `.env.beta` with a unique `VONAGE_APPLICATION_ID` and `SF_SANDBOX_URL`.
   - Configure a dedicated Cloud Run Service: `voice-agent-beta`.
3. **CI/CD Triggers**:
   - Setup GitHub Actions to trigger deployment to the **Beta Service** only on pushes to the `beta` branch.

---

## 📈 Phase 2: Expansion to All Branches
Once `beta` features are verified by the **ReviewerAgent**, they propagate through the hierarchy.

### 1. The Pull Request Gate
- No code enters `main` without passing through `beta` -> `staging`.
- Use **Thought Signatures** in the UAT phase to audit AI reasoning before production deployment.

### 2. Infrastructure as Code (IaC)
- Use the provided `Dockerfile` and `deploy.sh` to replicate environments.
- **Scaling**: Increase concurrency in Cloud Run for `main` while keeping `beta` at 1 instance to minimize costs.

---

## 🛡️ Governance & Safety
- **Compliance Lock**: The `beta` branch handles mock data ([data/clients.csv](file:///Users/SoundComputer/Downloads/a2ac.ai/movement-voice-agent/data/clients.csv)).
- **Production Lock**: The `main` branch is the ONLY environment permitted to write to the Primary Salesforce Lead database.
- **Rollback Protocol**: In case of a "Hallucination Event," roll back the `main` service to the last stable SHA-256 commit within 60 seconds.

---
*Blueprint by Phil Hills AI Lab | Feb 2026*
