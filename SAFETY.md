# Safety & Responsibility Document

## Core Voice Agent - Security & Ethics Assessment

### 1. Threat Model

#### 1.1 Prompt Injection
**Risk**: Malicious users may attempt to manipulate the agent via adversarial inputs.

**Mitigations**:
- System prompt is immutable and loaded from secure configuration
- Gemini 3 safety filters enabled at API level
- Input sanitization removes control characters
- Response validation checks for policy violations

#### 1.2 Voice Cloning / Deepfake
**Risk**: Agent voice could be misused to impersonate individuals.

**Mitigations**:
- Agent uses synthetic voice with identifiable cadence
- SynthID watermarking recommended for production deployments
- Clear AI disclosure in opening statement

#### 1.3 Spam / Harassment
**Risk**: System could be used for illegal robocalling or harassment.

**Mitigations**:
- 11-touch cadence with configurable limits
- Do Not Call list integration
- Automatic opt-out handling
- Rate limiting per campaign

### 2. Safety Settings

The following Gemini API safety settings are enforced:

```python
safety_settings = {
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
    "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE"
}
```

### 3. Compliance Framework

| Regulation | Status | Implementation |
|------------|--------|----------------|
| TCPA | Compliant | Recording disclosure, time restrictions |
| GDPR | Partial | Data minimization, erasure on request |
| CCPA | Compliant | Opt-out mechanisms |
| FTC Guidelines | Compliant | AI disclosure, no deceptive practices |

### 4. Data Handling

#### 4.1 Data Collection
- Call recordings (with consent)
- Transcripts
- Lead disposition
- Contact preferences

#### 4.2 Data Retention
- Call recordings: 90 days default
- Transcripts: 1 year
- Contact preferences: Indefinite (for compliance)

#### 4.3 Data Deletion
- Automated deletion on opt-out
- Manual purge via API
- Right to erasure honored within 30 days

### 5. Incident Response

#### 5.1 Safety Incident Classification
| Level | Description | Response Time |
|-------|-------------|---------------|
| P0 | Active harm to users | Immediate shutdown |
| P1 | Policy violation detected | 4 hours |
| P2 | Potential misuse pattern | 24 hours |
| P3 | Documentation gap | 7 days |

#### 5.2 Escalation Path
1. Automated monitoring flags anomalies
2. Review by on-call engineer
3. Escalation to safety team if warranted
4. Incident report filed

### 6. Responsible AI Principles

This system adheres to Google's AI Principles:

1. **Be socially beneficial**: Designed to assist, not replace, human relationships
2. **Avoid creating or reinforcing bias**: Regular fairness audits
3. **Be built and tested for safety**: Comprehensive safety testing
4. **Be accountable to people**: Human oversight mechanisms
5. **Incorporate privacy design principles**: Data minimization
6. **Uphold scientific excellence**: Reproducible, documented architecture
7. **Made available for beneficial uses**: No weapons, surveillance, or rights violations

### 7. Known Limitations

- Cannot detect if caller is in distress
- May not recognize sarcasm or humor
- Limited ability to refuse unreasonable requests gracefully
- Conversational memory bounded by context window

### 8. Contact

For safety concerns or incident reports:
- Email: safety@philhills.ai
- Emergency: Disable via Cloud Run console

---

*Safety Document v1.0 | Last Updated: January 2026*
