# Model Card: Movement Voice Agent

## Model Details
- **Name**: Movement Voice Agent (Jason)
- **Version**: 1.0
- **Date**: January 2026
- **Authors**: Phil Hills AI Lab
- **License**: Apache 2.0
- **Architecture**: Talker-Reasoner Dual System with Q Protocol Orchestration

### Model Type
Autonomous voice agent utilizing Google Gemini 3 Flash Preview for real-time conversational AI with multi-channel tool orchestration.

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                  Q PROTOCOL ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐      ┌─────────────┐                      │
│  │ GCP         │◄────►│ Salesforce  │  Dual Orchestrators  │
│  │ Orchestrator│      │ AgentForce  │                      │
│  └──────┬──────┘      └──────┬──────┘                      │
│         │                    │                              │
│         └────────┬───────────┘                              │
│                  ▼                                          │
│         ┌───────────────┐                                   │
│         │  Memory Cube  │  Persistent Identity & Context   │
│         └───────┬───────┘                                   │
│                 ▼                                           │
│  ┌──────────────────────────────────┐                      │
│  │     TALKER-REASONER SYSTEM       │                      │
│  │  ┌─────────┐    ┌─────────────┐  │                      │
│  │  │ Talker  │◄──►│  Reasoner   │  │                      │
│  │  │(System 1)│   │ (System 2)  │  │                      │
│  │  │ <500ms  │    │ 2-5 sec     │  │                      │
│  │  └─────────┘    └─────────────┘  │                      │
│  └──────────────────────────────────┘                      │
│                  │                                          │
│                  ▼                                          │
│  ┌──────────────────────────────────┐                      │
│  │         TOOL EXECUTION           │                      │
│  │  📞 Outbound Calls (11-touch)    │                      │
│  │  📱 SMS  │  📧 Email             │                      │
│  │  📅 Calendar  │  🌐 Browser      │                      │
│  └──────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## Intended Use

### Primary Use Cases
- **Outbound Sales Calls**: Autonomous lead qualification and appointment booking
- **11-Touch Cadence**: Persistent follow-up over days/weeks with memory retention
- **Multi-Channel Orchestration**: Voice, SMS, Email, Calendar integration

### Out of Scope
- Medical advice or diagnosis
- Legal counsel
- Financial investment recommendations
- High-stakes autonomous decision making
- Impersonation of real individuals

## Factors

### Performance Factors
- **Audio Quality**: Optimal with high-quality microphone input; degrades with >60dB ambient noise
- **Accents**: Trained primarily on North American English; may have reduced accuracy with other accents
- **Network Latency**: Requires stable internet connection for <500ms TTFT (Time To First Token)

### Demographic Considerations
- Voice recognition calibrated for adult speech patterns
- May require adjustment for elderly or youth demographics

## Metrics

| Metric | Value | Method |
|--------|-------|--------|
| Time To First Token (TTFT) | <500ms | Gemini 3 ThinkingConfig: MINIMAL |
| Word Error Rate (WER) | <5% | Internal testing on conversational corpus |
| Appointment Booking Rate | Varies | Dependent on lead quality and campaign |

## Training Data
- **Model**: Google Gemini 3 Flash Preview
- **Fine-tuning**: None (uses system prompt engineering)
- **Context**: Mortgage industry sales conversations

## Ethical Considerations

### Potential Misuse
- Voice cloning for fraud
- Spam calling at scale
- Harassment via persistent contact

### Mitigations
1. **Disclosure**: Agent identifies as AI in opening statement
2. **Recording Notification**: TCPA-compliant recording disclaimer
3. **Safety Filters**: Gemini API safety settings enabled:
   - `HARM_CATEGORY_HARASSMENT: BLOCK_MEDIUM_AND_ABOVE`
   - `HARM_CATEGORY_HATE_SPEECH: BLOCK_MEDIUM_AND_ABOVE`
4. **Rate Limiting**: Built-in cadence controls
5. **Do Not Call Compliance**: Respects opt-out requests

## Limitations

1. **Context Window**: May lose context in very long conversations (>30 minutes)
2. **Emotional Intelligence**: Limited ability to detect subtle emotional cues
3. **Multi-Speaker**: Not optimized for conference call scenarios
4. **Languages**: English only in current version

## Caveats and Recommendations

- **Human Oversight**: Recommend periodic review of conversation logs
- **Escalation Path**: Configure warm transfer to human agents for complex scenarios
- **Compliance**: Users responsible for local telecommunication regulations

---

## Citing This Work

```bibtex
@software{movement_voice_agent_2026,
  author = {Hills, Phil},
  title = {Movement Voice Agent: Autonomous AI Sales Agent with Q Protocol},
  year = {2026},
  publisher = {Phil Hills AI Lab},
  url = {https://github.com/Phil-Hills/movement-voice-agent}
}
```

---

*Model Card version 1.0 | Last updated: January 2026*
